from activity.models import ActivityListGroup
from common.mixins import AuthPermissionMixin
from django.utils import timezone
from django.views.generic import TemplateView
from group.models import GroupStudent


class StudentDashboardView(AuthPermissionMixin, TemplateView):
    template_name = 'student/dashboard.html'

    def get_enrollments(self):
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

    def get_activity_links(self, group_ids):
        return (
            ActivityListGroup.objects
            .filter(
                group_id__in=group_ids,
                activity_list__deleted_at__isnull=True,
            )
            .select_related('activity_list', 'group')
        )

    def get_activity_status(self, activity_link):
        now = timezone.now()

        if activity_link.starts_at and activity_link.starts_at > now:
            return 'future'

        if activity_link.ends_at and activity_link.ends_at < now:
            return 'closed'

        return 'open'

    def add_activity_totals(self, enrollments, activity_links):
        totals_by_group = {
            enrollment.group_id: {
                'open': 0,
                'future': 0,
                'closed': 0,
            }
            for enrollment in enrollments
        }

        for activity_link in activity_links:
            status = self.get_activity_status(activity_link)
            totals_by_group[activity_link.group_id][status] += 1

        for enrollment in enrollments:
            enrollment.activity_totals = totals_by_group[enrollment.group_id]

    def get_context_data(self, **kwargs):
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
