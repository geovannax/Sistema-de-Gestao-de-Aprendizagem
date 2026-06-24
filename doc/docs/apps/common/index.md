# common

O app **common** centraliza todos os componentes reutilizáveis do projeto: a view genérica de listagem, mixins de view, utilitários e filtros de template. É a camada de infraestrutura compartilhada entre os demais apps.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| generic | [EnhancedListView](generic/EnhancedListView.md) |
| mixins | [AuthPermissionMixin](mixins/AuthPermissionMixin.md), [HTMXLoginRequiredMixin](mixins/HTMXLoginRequiredMixin.md), [FilteringMixin](mixins/FilteringMixin.md), [OrderingMixin](mixins/OrderingMixin.md), e mais |
| views | [LandingPage](views/LandingPage.md), [HomeView](views/HomeView.md), [permission_denied](views/permission_denied.md), [page_not_found](views/page_not_found.md) |
| utils | [get_btn_action](utils/get_btn_action.md) |
| filters | [get_attr](filters/get_attr.md), [get_attr_with_truncate](filters/get_attr_with_truncate.md), [get_model_only_fields](filters/get_model_only_fields.md), [get_item](filters/get_item.md) |
