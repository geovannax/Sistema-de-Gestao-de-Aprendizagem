from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from decimal import Decimal

from activity.models import ActivityListGroup, Exercise
from common.mixins import AuthPermissionMixin
from django.db.models import Case, Count, DecimalField, Sum, When
from django.utils import timezone
from django.views.generic import TemplateView
from group.models import GroupStudent
from student.models import ExerciseAnswer, Submission


class ProfileView(AuthPermissionMixin, TemplateView):
    template_name = 'accounts/profile.html'

    @staticmethod
    def _grade_class(pct: float) -> str:
        if pct >= 90: return 'a'
        if pct >= 70: return 'b'
        if pct >= 50: return 'c'
        return 'd'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        context['full_name'] = user.get_full_name() or user.username
        parts = (user.get_full_name() or user.username).split()
        context['initials'] = ''.join(p[0].upper() for p in parts[:2])

        # Turmas ativas do aluno
        enrollments = list(
            GroupStudent.objects
            .filter(student=user, is_active=True, group__deleted_at__isnull=True)
            .select_related('group', 'group__created_by')
            .order_by('group__name')
        )
        group_ids = [e.group_id for e in enrollments]

        # Activity links para todas as turmas matriculadas
        activity_links = list(
            ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .select_related('activity_list', 'group')
            .order_by('group_id', 'assigned_at')
        )

        # Pontuação máxima por activity_list (exercícios não anulados)
        activity_list_ids = list({lk.activity_list_id for lk in activity_links})
        max_pts_qs = (
            Exercise.objects
            .filter(activity_list_id__in=activity_list_ids, is_annulled=False)
            .values('activity_list_id')
            .annotate(max_pts=Sum('points', output_field=DecimalField()))
        )
        max_pts_by_list = {row['activity_list_id']: float(row['max_pts'] or 0) for row in max_pts_qs}
        link_max_pts = {lk.pk: max_pts_by_list.get(lk.activity_list_id, 0.0) for lk in activity_links}

        # Submissões finalizadas do aluno
        link_ids = [lk.pk for lk in activity_links]
        all_subs = list(
            Submission.objects
            .filter(
                student=user,
                activity_link_id__in=link_ids,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
        )
        sub_ids = [s.pk for s in all_subs]

        # Pontuação earned por submissão
        score_map = {
            s['submission_id']: s
            for s in ExerciseAnswer.objects
            .filter(submission_id__in=sub_ids, exercise__is_annulled=False)
            .values('submission_id')
            .annotate(
                earned=Sum(
                    Case(When(is_correct=True, then='exercise__points'),
                         default=Decimal(0), output_field=DecimalField())
                ),
            )
        }

        # Submissão por activity_link_id (uma por link para este aluno)
        sub_by_link = {sub.activity_link_id: sub for sub in all_subs}

        # Agrupar links por turma
        links_by_group: dict[int, list] = defaultdict(list)
        for lk in activity_links:
            links_by_group[lk.group_id].append(lk)

        groups_grades = []
        for enr in enrollments:
            gid = enr.group_id
            g_links = links_by_group.get(gid, [])
            grand_total = sum(link_max_pts.get(lk.pk, 0.0) for lk in g_links)
            total_earned = 0.0
            activities_submitted = 0
            breakdown = []

            for link in g_links:
                link_total = link_max_pts.get(link.pk, 0.0)
                sub = sub_by_link.get(link.pk)
                if sub:
                    e = float(score_map.get(sub.pk, {}).get('earned') or 0)
                    pct = round(e / link_total * 100) if link_total else 0
                    total_earned += e
                    activities_submitted += 1
                    breakdown.append({
                        'title': link.activity_list.title,
                        'submitted': True,
                        'earned_fmt': f'{e:.0f}',
                        'total_fmt': f'{link_total:.0f}' if link_total else '—',
                        'pct': pct,
                        'submitted_at': sub.submitted_at,
                        'grade_class': self._grade_class(pct),
                    })
                else:
                    overdue = bool(link.ends_at and link.ends_at < now)
                    breakdown.append({
                        'title': link.activity_list.title,
                        'submitted': False,
                        'is_overdue': overdue,
                        'earned_fmt': '0',
                        'total_fmt': f'{link_total:.0f}' if link_total else '—',
                        'pct': 0,
                        'submitted_at': None,
                        'grade_class': 'd',
                    })

            overall_pct = round(total_earned / grand_total * 100) if grand_total else 0
            teacher = enr.group.created_by
            groups_grades.append({
                'name': enr.group.name,
                'teacher': teacher.get_full_name() or teacher.username,
                'submitted': activities_submitted > 0,
                'activities': activities_submitted,
                'total_activities': len(g_links),
                'earned_fmt': f'{total_earned:.0f}',
                'total_fmt': f'{grand_total:.0f}' if grand_total else '—',
                'pct': overall_pct,
                'grade_class': self._grade_class(overall_pct),
                'breakdown': breakdown,
            })

        context['groups_grades'] = groups_grades
        context['total_submitted'] = sum(g['activities'] for g in groups_grades)
        context['total_acts'] = sum(g['total_activities'] for g in groups_grades)
        context['total_pending'] = context['total_acts'] - context['total_submitted']
        return context


class OverviewView(AuthPermissionMixin, TemplateView):
    template_name = 'accounts/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['full_name'] = user.get_full_name() or user.username
        parts = (user.get_full_name() or user.username).split()
        context['initials'] = ''.join(p[0].upper() for p in parts[:2])

        group_ids = list(
            GroupStudent.objects
            .filter(student=user, is_active=True, group__deleted_at__isnull=True)
            .values_list('group_id', flat=True)
        )

        total_by_group = {
            row['group_id']: row['total']
            for row in ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .values('group_id')
            .annotate(total=Count('pk'))
        }

        submitted_by_group = {
            row['activity_link__group_id']: row['count']
            for row in Submission.objects
            .filter(
                student=user,
                activity_link__group_id__in=group_ids,
                activity_link__activity_list__deleted_at__isnull=True,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .values('activity_link__group_id')
            .annotate(count=Count('pk'))
        }

        total_atividades = sum(total_by_group.values())
        total_concluidas = sum(submitted_by_group.values())

        activity_links = list(
            ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .select_related('activity_list', 'group')
        )
        link_ids = [lk.pk for lk in activity_links]

        submitted_link_ids = set(
            Submission.objects
            .filter(
                student=user,
                activity_link_id__in=link_ids,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .values_list('activity_link_id', flat=True)
        )

        activity_list_ids = [lk.activity_list_id for lk in activity_links]
        exercise_count_by_list = {
            row['activity_list_id']: row['total']
            for row in Exercise.objects
            .filter(activity_list_id__in=activity_list_ids, is_annulled=False)
            .values('activity_list_id')
            .annotate(total=Count('pk'))
        }

        now = timezone.now()
        upcoming = []
        for lk in activity_links:
            if lk.pk in submitted_link_ids:
                continue
            ends = lk.ends_at
            if ends:
                delta = (ends - now).total_seconds() / 86400
                if delta < 0:
                    urgency, stripe = 'overdue', '#ef4444'
                elif delta < 2:
                    urgency, stripe = 'urgent', '#ef4444'
                elif delta < 7:
                    urgency, stripe = 'upcoming', '#f59e0b'
                else:
                    urgency, stripe = 'normal', '#3b82f6'
            else:
                urgency, stripe = 'none', '#94a3b8'
            upcoming.append({
                'link': lk,
                'title': lk.activity_list.title,
                'group_name': lk.group.name,
                'ends_at': ends,
                'urgency': urgency,
                'stripe': stripe,
                'total_exercises': exercise_count_by_list.get(lk.activity_list_id, 0),
            })

        _max_dt = _dt.datetime(9999, 12, 31, tzinfo=_dt.timezone.utc)
        upcoming.sort(key=lambda x: (
            2 if x['urgency'] == 'overdue' else (1 if x['ends_at'] is None else 0),
            x['ends_at'] if x['ends_at'] is not None else _max_dt,
        ))

        # Timeline: recent completed submissions
        recent_subs = list(
            Submission.objects
            .filter(
                student=user,
                activity_link__group_id__in=group_ids,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .select_related('activity_link__activity_list', 'activity_link__group')
            .order_by('-submitted_at')[:5]
        )
        if recent_subs:
            sub_ids = [s.pk for s in recent_subs]
            score_map = {
                row['submission_id']: row
                for row in ExerciseAnswer.objects
                .filter(submission_id__in=sub_ids, exercise__is_annulled=False)
                .values('submission_id')
                .annotate(
                    earned=Sum(
                        Case(When(is_correct=True, then='exercise__points'),
                             default=Decimal(0), output_field=DecimalField())
                    ),
                    total_pts=Sum('exercise__points', output_field=DecimalField()),
                )
            }
        else:
            score_map = {}

        timeline = []
        for sub in recent_subs:
            sc = score_map.get(sub.pk, {})
            earned = float(sc.get('earned') or 0)
            total_pts = float(sc.get('total_pts') or 0)
            pct = round(earned / total_pts * 100) if total_pts else None
            timeline.append({
                'title': sub.activity_link.activity_list.title,
                'group_name': sub.activity_link.group.name,
                'submitted_at': sub.submitted_at,
                'link_pk': sub.activity_link_id,
                'pct': pct,
                'earned_fmt': f'{earned:.1f}' if sc else None,
                'total_fmt': f'{total_pts:.1f}' if sc else None,
            })

        context.update({
            'upcoming': upcoming[:5],
            'timeline': timeline,
            'total_turmas': len(group_ids),
            'total_atividades': total_atividades,
            'total_concluidas': total_concluidas,
            'total_pendentes': total_atividades - total_concluidas,
        })
        return context


class PendingView(AuthPermissionMixin, TemplateView):
    template_name = 'accounts/pending.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['full_name'] = user.get_full_name() or user.username
        parts = (user.get_full_name() or user.username).split()
        context['initials'] = ''.join(p[0].upper() for p in parts[:2])

        enrollments = list(
            GroupStudent.objects
            .filter(student=user, is_active=True, group__deleted_at__isnull=True)
            .values_list('group_id', flat=True)
        )

        activity_links = list(
            ActivityListGroup.objects
            .filter(group_id__in=enrollments, activity_list__deleted_at__isnull=True)
            .select_related('activity_list', 'group', 'group__created_by')
        )

        submitted_link_ids = set(
            Submission.objects
            .filter(
                student=user,
                activity_link_id__in=[lk.pk for lk in activity_links],
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .values_list('activity_link_id', flat=True)
        )

        activity_list_ids = [lk.activity_list_id for lk in activity_links]
        exercise_count_by_list = {
            row['activity_list_id']: row['total']
            for row in Exercise.objects
            .filter(activity_list_id__in=activity_list_ids, is_annulled=False)
            .values('activity_list_id')
            .annotate(total=Count('pk'))
        }

        now = timezone.now()
        pending = []
        for link in activity_links:
            if link.pk in submitted_link_ids:
                continue
            ends = link.ends_at
            if ends:
                delta_days = (ends - now).total_seconds() / 86400
                if delta_days < 0:
                    urgency = 'overdue'
                    stripe = '#ef4444'
                elif delta_days < 2:
                    urgency = 'urgent'
                    stripe = '#ef4444'
                elif delta_days < 7:
                    urgency = 'upcoming'
                    stripe = '#f59e0b'
                else:
                    urgency = 'normal'
                    stripe = '#3b82f6'
            else:
                urgency = 'none'
                stripe = '#94a3b8'

            pending.append({
                'link': link,
                'title': link.activity_list.title,
                'group_name': link.group.name,
                'teacher': link.group.created_by.get_full_name() or link.group.created_by.username,
                'ends_at': ends,
                'urgency': urgency,
                'stripe': stripe,
                'total_exercises': exercise_count_by_list.get(link.activity_list_id, 0),
            })

        _max_dt = _dt.datetime(9999, 12, 31, tzinfo=_dt.timezone.utc)
        pending.sort(key=lambda x: (
            2 if x['urgency'] == 'overdue' else (1 if x['ends_at'] is None else 0),
            x['ends_at'] if x['ends_at'] is not None else _max_dt,
        ))

        context['pending'] = pending
        context['pending_count'] = len(pending)
        return context


class TurmasView(AuthPermissionMixin, TemplateView):
    template_name = 'accounts/turmas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['full_name'] = user.get_full_name() or user.username
        parts = (user.get_full_name() or user.username).split()
        context['initials'] = ''.join(p[0].upper() for p in parts[:2])

        enrollments = list(
            GroupStudent.objects
            .filter(student=user, is_active=True, group__deleted_at__isnull=True)
            .select_related('group', 'group__created_by')
            .order_by('group__name')
        )
        group_ids = [e.group_id for e in enrollments]

        total_by_group = {
            row['group_id']: row['total']
            for row in ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .values('group_id')
            .annotate(total=Count('pk'))
        }

        submitted_by_group = {
            row['activity_link__group_id']: row['count']
            for row in Submission.objects
            .filter(
                student=user,
                activity_link__group_id__in=group_ids,
                activity_link__activity_list__deleted_at__isnull=True,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .values('activity_link__group_id')
            .annotate(count=Count('pk'))
        }

        turmas = []
        for enr in enrollments:
            g = enr.group
            total = total_by_group.get(g.pk, 0)
            submitted = submitted_by_group.get(g.pk, 0)
            pct = round(submitted / total * 100) if total else 0
            turmas.append({
                'pk': g.pk,
                'name': g.name,
                'teacher': g.created_by.get_full_name() or g.created_by.username,
                'total': total,
                'submitted': submitted,
                'pending': total - submitted,
                'pct': pct,
            })

        context['turmas'] = turmas
        return context
