from common.mixins import ActionsMixin, FilteringMixin, NavigationMixin, OrderingMixin, ViewTypeMixin
from django.views.generic import ListView


class EnhancedListView(
    NavigationMixin,
    FilteringMixin,
    OrderingMixin,
    ViewTypeMixin,
    ActionsMixin,
    ListView
):
    create_url = None
    detail_url = None
    page_description = None
    page_title = None
    paginate_by = 10
    template_name = 'global/partials/generic/list/view.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self.apply_filtering(queryset)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': self.page_title,
            'page_description': self.page_description,
            'create_url': self.create_url,
            'detail_url': self.detail_url,
            'view_type': self.get_view_type(),
            **self.has_filtering(return_context=True),
            **self.has_ordering(return_context=True),
        })
        return context
