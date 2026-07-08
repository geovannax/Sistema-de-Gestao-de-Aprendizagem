"""Views do app student."""
from __future__ import annotations

from typing import Any

from activity.models import ActivityListGroup, Exercise, ExerciseOption
from common.mixins import AuthPermissionMixin
from django.db.models import Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from group.models import Group, GroupSharing, GroupStudent
from student.models import ExerciseAnswer, Submission


class StudentDashboardView(AuthPermissionMixin, TemplateView):
    """Dashboard principal do aluno.

    Exibe todas as turmas em que o aluno está matriculado e um resumo
    de atividades por status (abertas, futuras e encerradas) para cada turma.
    """

    template_name = 'student/dashboard.html'

    def get_enrollments(self) -> QuerySet[GroupStudent]:
        """Retorna as matrículas ativas do aluno em turmas não deletadas."""
        return (
            GroupStudent.objects
            .filter(
                student=self.request.user,
                is_active=True,
                group__deleted_at__isnull=True,
            )
            .select_related('group', 'group__created_by')
            .order_by('-joined_at')
        )

    def get_activity_links(self, group_ids: list[int]) -> QuerySet[ActivityListGroup]:
        """Retorna os vínculos de atividades para um conjunto de turmas."""
        submitted_links = Submission.objects.filter(
            student=self.request.user,
            submitted_at__isnull=False,
        ).values('activity_link_id')
        return (
            ActivityListGroup.objects
            .filter(group_id__in=group_ids)
            .filter(
                Q(activity_list__deleted_at__isnull=True) |
                Q(pk__in=submitted_links)
            )
            .select_related('activity_list', 'group')
        )

    def get_activity_status(self, activity_link: ActivityListGroup) -> str:
        """Calcula o status de disponibilidade de uma atividade vinculada."""
        now = timezone.now()
        if activity_link.starts_at and activity_link.starts_at > now:
            return 'future'
        if activity_link.ends_at and activity_link.ends_at < now:
            return 'closed'
        return 'open'

    def add_activity_totals(
        self,
        enrollments: list[GroupStudent],
        activity_links: list[ActivityListGroup],
    ) -> None:
        """Agrega os totais de atividades por status em cada matrícula."""
        totals_by_group = {
            enrollment.group_id: {'open': 0, 'future': 0, 'closed': 0}
            for enrollment in enrollments
        }
        for activity_link in activity_links:
            status = self.get_activity_status(activity_link)
            totals_by_group[activity_link.group_id][status] += 1
        for enrollment in enrollments:
            enrollment.activity_totals = totals_by_group[enrollment.group_id]

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        enrollments = list(self.get_enrollments())
        group_ids = [enrollment.group_id for enrollment in enrollments]
        activity_links = list(self.get_activity_links(group_ids))
        view_type = self.request.GET.get('view_type', 'cards')
        if view_type not in ['cards', 'table']:
            view_type = 'cards'
        self.add_activity_totals(enrollments, activity_links)
        context.update({
            'page_title': 'Área do Aluno',
            'page_description': 'Acompanhe suas turmas e atividades disponíveis em um só lugar.',
            'enrollments': enrollments,
            'view_type': view_type,
        })
        return context


class StudentGroupDetailView(AuthPermissionMixin, TemplateView):
    """Detalhes de uma turma na visão do aluno.

    Exibe as atividades vinculadas à turma com o status de disponibilidade
    e os botões de ação (Iniciar / Continuar / Ver Resultado) por atividade.
    Levanta 404 se o aluno não estiver matriculado na turma.
    """

    template_name = 'student/group_detail.html'

    STATUS_LABELS = {
        'open': ('open', 'Aberta'),
        'future': ('future', 'Em breve'),
        'closed': ('closed', 'Encerrada'),
    }

    def get_enrollment(self) -> GroupStudent:
        """Retorna a matrícula ativa do aluno na turma solicitada."""
        try:
            return (
                GroupStudent.objects
                .select_related('group', 'group__created_by')
                .get(
                    group_id=self.kwargs['pk'],
                    student=self.request.user,
                    is_active=True,
                    group__deleted_at__isnull=True,
                )
            )
        except GroupStudent.DoesNotExist:
            raise Http404

    def get_activity_links(self, group: Group) -> list[ActivityListGroup]:
        """Retorna as atividades da turma com status e submissão anotados."""
        submitted_links = Submission.objects.filter(
            student=self.request.user,
            submitted_at__isnull=False,
        ).values('activity_link_id')
        links = list(
            ActivityListGroup.objects
            .filter(group=group)
            .filter(
                Q(activity_list__deleted_at__isnull=True) |
                Q(pk__in=submitted_links)
            )
            .select_related('activity_list')
            .order_by('-assigned_at')
        )
        now = timezone.now()
        for link in links:
            if link.starts_at and link.starts_at > now:
                status_key = 'future'
            elif link.ends_at and link.ends_at < now:
                status_key = 'closed'
            else:
                status_key = 'open'
            link.status_class, link.status_label = self.STATUS_LABELS[status_key]

        # Annotate each link with the student's submission (if any)
        link_ids = [link.pk for link in links]
        submissions = {
            s.activity_link_id: s
            for s in Submission.objects.filter(
                student=self.request.user,
                activity_link_id__in=link_ids,
            )
        }
        for link in links:
            link.submission = submissions.get(link.pk)

        return links

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        enrollment = self.get_enrollment()
        activity_links = self.get_activity_links(enrollment.group)
        pending_links = [l for l in activity_links if not (l.submission and l.submission.submitted_at)]
        completed_links = [l for l in activity_links if l.submission and l.submission.submitted_at]
        context.update({
            'enrollment': enrollment,
            'group': enrollment.group,
            'activity_links': activity_links,
            'pending_links': pending_links,
            'completed_links': completed_links,
        })
        return context


# ---------------------------------------------------------------------------
# Student Activity (resolver atividade)
# ---------------------------------------------------------------------------

class _ActivityAccessMixin(AuthPermissionMixin):
    """Valida acesso do aluno a um ActivityListGroup."""

    def get_activity_link(self) -> ActivityListGroup:
        try:
            link = (
                ActivityListGroup.objects
                .select_related('activity_list', 'group')
                .get(
                    pk=self.kwargs['link_pk'],
                    activity_list__deleted_at__isnull=True,
                )
            )
        except ActivityListGroup.DoesNotExist:
            raise Http404

        if not GroupStudent.objects.filter(
            group=link.group,
            student=self.request.user,
            is_active=True,
            group__deleted_at__isnull=True,
        ).exists():
            raise Http404

        return link


class StudentActivityView(_ActivityAccessMixin, TemplateView):
    """Página de resolução de uma atividade pelo aluno.

    Carrega ou cria a :class:`~student.models.Submission` do aluno.
    GET padrão retorna a página completa; GET com ``HX-Request`` retorna
    apenas o fragmento ``_activity_main.html`` (sidebar + exercício atual).
    POST salva a resposta do exercício corrente e renderiza o próximo.
    POST com ``go_review=1`` redireciona para a tela de revisão após salvar.
    """

    template_name = 'student/activity_detail.html'

    # ------------------------------------------------------------------
    # Helpers compartilhados entre GET e POST
    # ------------------------------------------------------------------

    def _get_or_create_submission(self, activity_link: ActivityListGroup) -> Submission:
        submission, _ = Submission.objects.get_or_create(
            student=self.request.user,
            activity_link=activity_link,
        )
        return submission

    def _build_exercises(
        self, activity_link: ActivityListGroup
    ) -> list[Exercise]:
        return list(
            activity_link.activity_list.exercises
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related('multiple_choice_exercise__options', 'code_exercise__test_cases')
        )

    def _build_context(
        self,
        activity_link: ActivityListGroup,
        submission: Submission,
        navigate_to_pk: int | None,
    ) -> dict:
        exercises = self._build_exercises(activity_link)
        answers = {
            a.exercise_id: a
            for a in submission.answers.select_related('selected_option').all()
        }

        # Determine the current exercise
        current_exercise: Exercise | None = None
        if navigate_to_pk:
            current_exercise = next(
                (ex for ex in exercises if ex.pk == navigate_to_pk), None
            )
        if current_exercise is None and exercises:
            current_exercise = exercises[0]

        current_index = 0
        for i, ex in enumerate(exercises):
            ex.is_answered = ex.pk in answers
            ex.answer = answers.get(ex.pk)
            ex.is_current = current_exercise is not None and ex.pk == current_exercise.pk
            ex.nav_index = i + 1
            if ex.is_current:
                current_index = i

        prev_exercise = exercises[current_index - 1] if current_index > 0 else None
        next_exercise = (
            exercises[current_index + 1]
            if current_index < len(exercises) - 1
            else None
        )
        answered_count = sum(1 for ex in exercises if ex.is_answered)
        total = len(exercises)
        answered_percent = round(answered_count / total * 100) if total else 0

        return {
            'activity_link': activity_link,
            'submission': submission,
            'exercises': exercises,
            'current_exercise': current_exercise,
            'current_answer': answers.get(current_exercise.pk) if current_exercise else None,
            'answered_count': answered_count,
            'total_exercises': total,
            'prev_exercise': prev_exercise,
            'next_exercise': next_exercise,
            'current_index': current_index + 1,
            'answered_percent': answered_percent,
        }

    def _save_answer(
        self,
        submission: Submission,
        exercise: Exercise,
        post_data: dict,
    ) -> None:
        observation = post_data.get('student_observation', '').strip()
        defaults: dict = {
            'answer_text': '',
            'selected_option': None,
            'is_correct': None,
            'student_observation': observation,
        }

        if exercise.type == 'multiple_choice':
            option_pk_str = post_data.get('selected_option', '')
            if option_pk_str and option_pk_str.isdigit():
                try:
                    option = ExerciseOption.objects.get(
                        pk=int(option_pk_str),
                        exercise=exercise.multiple_choice_exercise,
                    )
                    defaults['selected_option'] = option
                    defaults['is_correct'] = option.is_correct
                except ExerciseOption.DoesNotExist:
                    pass
        else:
            defaults['answer_text'] = post_data.get('answer_text', '').strip()

        # Persist or delete based on whether there is content
        has_content = defaults['selected_option'] is not None or defaults['answer_text'] or observation
        if has_content:
            ExerciseAnswer.objects.update_or_create(
                submission=submission,
                exercise=exercise,
                defaults=defaults,
            )
        else:
            ExerciseAnswer.objects.filter(submission=submission, exercise=exercise).delete()

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
        ).first()

        if submission and submission.submitted_at:
            return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])

        if not submission:
            submission = Submission.objects.create(
                student=request.user,
                activity_link=activity_link,
            )

        navigate_to_str = request.GET.get('exercise', '')
        navigate_to_pk = int(navigate_to_str) if navigate_to_str.isdigit() else None

        context = self._build_context(activity_link, submission, navigate_to_pk)

        if request.headers.get('HX-Request'):
            return render(request, 'student/partials/_activity_main.html', context)
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        submission = self._get_or_create_submission(activity_link)

        if submission.submitted_at:
            return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])

        # Save the current exercise answer
        current_pk_str = request.POST.get('current_exercise_pk', '')
        if current_pk_str.isdigit():
            try:
                exercise = Exercise.objects.select_related(
                    'multiple_choice_exercise'
                ).get(
                    pk=int(current_pk_str),
                    activity_list=activity_link.activity_list,
                )
                self._save_answer(submission, exercise, request.POST)
            except Exercise.DoesNotExist:
                pass

        # Redirect to review page after saving
        if request.POST.get('go_review') == '1':
            review_url = reverse('student:activity_review', kwargs={'link_pk': activity_link.pk})
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = review_url
                return response
            return redirect(review_url)

        # Determine where to navigate after saving
        navigate_to_str = request.POST.get('navigate_to_pk', current_pk_str)
        navigate_to_pk = int(navigate_to_str) if navigate_to_str.isdigit() else None

        context = self._build_context(activity_link, submission, navigate_to_pk)

        if request.headers.get('HX-Request'):
            return render(request, 'student/partials/_activity_main.html', context)
        return render(request, self.template_name, context)


class StudentActivityReviewView(_ActivityAccessMixin, TemplateView):
    """Tela de revisão das respostas antes da submissão final.

    Exibe todos os exercícios com as respostas do aluno sem indicadores de
    acerto/erro. Alerta sobre exercícios sem resposta e permite ao aluno
    voltar para editar ou confirmar a entrega.
    """

    template_name = 'student/activity_review.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
        ).first()

        if not submission:
            return redirect('student:activity', link_pk=self.kwargs['link_pk'])
        if submission.submitted_at:
            return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])

        self._activity_link = activity_link
        self._submission = submission
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        activity_link = self._activity_link
        submission = self._submission

        exercises = list(
            activity_link.activity_list.exercises
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related('multiple_choice_exercise__options', 'code_exercise__test_cases')
        )

        answers = {
            a.exercise_id: a
            for a in submission.answers.select_related('selected_option').all()
        }

        for ex in exercises:
            ex.answer = answers.get(ex.pk)

        unanswered_count = sum(1 for ex in exercises if not ex.answer)

        context.update({
            'activity_link': activity_link,
            'submission': submission,
            'exercises': exercises,
            'unanswered_count': unanswered_count,
            'total_exercises': len(exercises),
            'answered_count': len(answers),
        })
        return context


class _TeacherAccessMixin(AuthPermissionMixin):
    """Verifica que o usuário é o dono da turma do ActivityListGroup."""

    def get_activity_link(self) -> ActivityListGroup:
        try:
            link = (
                ActivityListGroup.objects
                .select_related('activity_list', 'group', 'group__created_by')
                .get(
                    pk=self.kwargs['link_pk'],
                    activity_list__deleted_at__isnull=True,
                )
            )
        except ActivityListGroup.DoesNotExist:
            raise Http404
        if link.group.created_by != self.request.user:
            if not GroupSharing.objects.filter(
                group=link.group,
                shared_with=self.request.user,
                is_active=True,
            ).exists():
                raise Http404
        return link


class TeacherSubmissionsView(_TeacherAccessMixin, TemplateView):
    """Lista todos os alunos matriculados na turma, separados por status de entrega."""

    template_name = 'student/teacher_submissions.html'

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        activity_link = self.get_activity_link()

        # All submitted submissions
        submitted = list(
            Submission.objects.filter(
                activity_link=activity_link,
                submitted_at__isnull=False,
            )
            .select_related('student')
            .order_by('submitted_at')
        )

        submitted_student_ids = {s.student_id for s in submitted}
        total_exercises = activity_link.activity_list.exercises.count()

        for sub in submitted:
            answers = list(sub.answers.all())
            sub.answered_count = len(answers)
            sub.pending_count = sum(1 for a in answers if a.is_correct is None)
            sub.correct_count = sum(1 for a in answers if a.is_correct is True)

        # Students with an in-progress (not submitted) submission
        in_progress_ids = set(
            Submission.objects.filter(
                activity_link=activity_link,
                submitted_at__isnull=True,
            ).values_list('student_id', flat=True)
        )

        # All enrolled students who have NOT submitted
        pending_enrollments = list(
            GroupStudent.objects.filter(
                group=activity_link.group,
                is_active=True,
            )
            .select_related('student')
            .exclude(student_id__in=submitted_student_ids)
            .order_by('student__first_name', 'student__username')
        )

        for enrollment in pending_enrollments:
            enrollment.in_progress = enrollment.student_id in in_progress_ids

        context.update({
            'activity_link': activity_link,
            'submissions': submitted,
            'pending_enrollments': pending_enrollments,
            'total_exercises': total_exercises,
            'total_enrolled': len(submitted) + len(pending_enrollments),
        })
        return context


class TeacherGradeView(_TeacherAccessMixin, View):
    """Correção manual de uma submissão pelo professor.

    Salva acerto/erro por questão, comentário por questão e comentário geral.
    """

    template_name = 'student/teacher_grade.html'

    def _get_submission(self, activity_link: ActivityListGroup) -> Submission:
        try:
            return (
                Submission.objects
                .select_related('student')
                .get(
                    pk=self.kwargs['submission_pk'],
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                )
            )
        except Submission.DoesNotExist:
            raise Http404

    def _build_context(self, activity_link: ActivityListGroup, submission: Submission) -> dict:
        exercises = list(
            activity_link.activity_list.exercises
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related('multiple_choice_exercise__options', 'code_exercise__test_cases')
        )
        answers = {
            a.exercise_id: a
            for a in submission.answers.select_related('selected_option').all()
        }
        for ex in exercises:
            ex.answer = answers.get(ex.pk)

        return {
            'activity_link': activity_link,
            'submission': submission,
            'exercises': exercises,
        }

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        submission = self._get_submission(activity_link)
        return render(request, self.template_name, self._build_context(activity_link, submission))

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        submission = self._get_submission(activity_link)

        grade_updates: dict[int, bool] = {}
        comment_updates: dict[int, str] = {}

        for key, value in request.POST.items():
            if key.startswith('grade_') and value in ('correct', 'incorrect'):
                answer_pk_str = key[6:]
                if answer_pk_str.isdigit():
                    grade_updates[int(answer_pk_str)] = (value == 'correct')
            elif key.startswith('comment_answer_'):
                answer_pk_str = key[15:]
                if answer_pk_str.isdigit():
                    comment_updates[int(answer_pk_str)] = value.strip()

        all_pks = set(grade_updates) | set(comment_updates)
        for pk in all_pks:
            update_data: dict = {}
            if pk in grade_updates:
                update_data['is_correct'] = grade_updates[pk]
            if pk in comment_updates:
                update_data['teacher_comment'] = comment_updates[pk]
            if update_data:
                ExerciseAnswer.objects.filter(pk=pk, submission=submission).update(**update_data)

        submission.teacher_comment = request.POST.get('teacher_comment', '').strip()
        submission.save(update_fields=['teacher_comment'])

        messages.success(request, 'Correção enviada com sucesso!')
        return redirect('student:activity_submissions', link_pk=activity_link.pk)


class StudentSubmitView(_ActivityAccessMixin, View):
    """Submissão final de uma atividade pelo aluno.

    Marca ``submitted_at`` na Submission e redireciona para os resultados.
    Idempotente: se já submetido, apenas redireciona.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()

        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
        ).first()

        if not submission:
            raise Http404

        if not submission.submitted_at:
            submission.submitted_at = timezone.now()
            submission.save(update_fields=['submitted_at'])

        return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])


class StudentFeedbackView(_ActivityAccessMixin, View):
    """Salva o feedback geral do aluno sobre a atividade após submissão."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()

        try:
            submission = Submission.objects.get(
                student=request.user,
                activity_link=activity_link,
                submitted_at__isnull=False,
            )
        except Submission.DoesNotExist:
            raise Http404

        submission.student_feedback = request.POST.get('student_feedback', '').strip()
        submission.save(update_fields=['student_feedback'])

        return redirect('student:group_detail', pk=activity_link.group.pk)


class StudentResultView(_ActivityAccessMixin, TemplateView):
    """Resultados de uma atividade submetida pelo aluno."""

    template_name = 'student/result.html'

    def get_activity_link(self) -> ActivityListGroup:
        try:
            link = (
                ActivityListGroup.objects
                .select_related('activity_list', 'group')
                .get(pk=self.kwargs['link_pk'])
            )
        except ActivityListGroup.DoesNotExist:
            raise Http404

        if not GroupStudent.objects.filter(
            group=link.group,
            student=self.request.user,
            is_active=True,
            group__deleted_at__isnull=True,
        ).exists():
            raise Http404

        if link.activity_list.deleted_at is not None:
            if not Submission.objects.filter(
                activity_link=link,
                student=self.request.user,
                submitted_at__isnull=False,
            ).exists():
                raise Http404

        return link

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()

        submission = (
            Submission.objects
            .filter(student=request.user, activity_link=activity_link)
            .first()
        )

        # Redirect to activity if not yet submitted
        if not submission or not submission.submitted_at:
            return redirect('student:activity', link_pk=self.kwargs['link_pk'])

        self._activity_link = activity_link
        self._submission = submission
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        activity_link = self._activity_link
        submission = self._submission

        exercises = list(
            activity_link.activity_list.exercises
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related('multiple_choice_exercise__options', 'code_exercise__test_cases')
        )

        answers = {
            a.exercise_id: a
            for a in submission.answers.select_related('selected_option').all()
        }

        for ex in exercises:
            ex.answer = answers.get(ex.pk)

        total_points = sum(float(ex.points) for ex in exercises)
        earned_points = sum(
            float(ex.points)
            for ex in exercises
            if (a := answers.get(ex.pk)) and a.is_correct
        )
        answered_count = len(answers)
        auto_graded = sum(
            1 for a in answers.values() if a.is_correct is not None
        )
        pending_review = answered_count - auto_graded
        score_pct = round(earned_points / total_points * 100) if total_points else 0

        context.update({
            'activity_link': activity_link,
            'submission': submission,
            'exercises': exercises,
            'total_points': total_points,
            'earned_points': earned_points,
            'answered_count': answered_count,
            'total_exercises': len(exercises),
            'auto_graded': auto_graded,
            'pending_review': pending_review,
            'score_pct': score_pct,
        })
        return context
