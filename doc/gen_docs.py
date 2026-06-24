import os

BASE = r"c:\Users\edgar\OneDrive\Documentos\GitHub\Sistema-de-Gestao-de-Aprendizagem\doc\docs\apps"

pages = [
    # accounts
    ("accounts/models/UserPreferences.md",       "UserPreferences",       "accounts.models.UserPreferences"),
    ("accounts/middleware/CookieMiddleware.md",  "CookieMiddleware",      "accounts.middleware.CookieMiddleware"),
    ("accounts/signals/on_login.md",             "on_login",              "accounts.signals.on_login"),
    ("accounts/signals/on_logout.md",            "on_logout",             "accounts.signals.on_logout"),
    # activity / models
    ("activity/models/ActivityList.md",          "ActivityList",          "activity.models.ActivityList"),
    ("activity/models/ActivityArchived.md",      "ActivityArchived",      "activity.models.ActivityArchived"),
    ("activity/models/ActivityListGroup.md",     "ActivityListGroup",     "activity.models.ActivityListGroup"),
    ("activity/models/Exercise.md",              "Exercise",              "activity.models.Exercise"),
    ("activity/models/CodeExercise.md",          "CodeExercise",          "activity.models.CodeExercise"),
    ("activity/models/CompleteCodeExercise.md",  "CompleteCodeExercise",  "activity.models.CompleteCodeExercise"),
    ("activity/models/MultipleChoiceExercise.md","MultipleChoiceExercise","activity.models.MultipleChoiceExercise"),
    ("activity/models/ExerciseOption.md",        "ExerciseOption",        "activity.models.ExerciseOption"),
    ("activity/models/DiscursiveExercise.md",    "DiscursiveExercise",    "activity.models.DiscursiveExercise"),
    # activity / views
    ("activity/views/ActivityListBaseView.md",              "ActivityListBaseView",              "activity.views.ActivityListBaseView"),
    ("activity/views/ActivityListView.md",                  "ActivityListView",                  "activity.views.ActivityListView"),
    ("activity/views/ActivityArchivedListView.md",          "ActivityArchivedListView",          "activity.views.ActivityArchivedListView"),
    ("activity/views/ActivityCreateOrUpdateView.md",        "ActivityCreateOrUpdateView",        "activity.views.ActivityCreateOrUpdateView"),
    ("activity/views/ActivityCreateView.md",                "ActivityCreateView",                "activity.views.ActivityCreateView"),
    ("activity/views/ActivityUpdateView.md",                "ActivityUpdateView",                "activity.views.ActivityUpdateView"),
    ("activity/views/ActivityDetailBaseView.md",            "ActivityDetailBaseView",            "activity.views.ActivityDetailBaseView"),
    ("activity/views/ActivityDetailView.md",                "ActivityDetailView",                "activity.views.ActivityDetailView"),
    ("activity/views/ActivityAssignView.md",                "ActivityAssignView",                "activity.views.ActivityAssignView"),
    ("activity/views/ActivityAssignUpdateView.md",          "ActivityAssignUpdateView",          "activity.views.ActivityAssignUpdateView"),
    ("activity/views/ActivityArchiveView.md",               "ActivityArchiveView",               "activity.views.ActivityArchiveView"),
    ("activity/views/ActivityDeleteView.md",                "ActivityDeleteView",                "activity.views.ActivityDeleteView"),
    ("activity/views/ActivityUnshareView.md",               "ActivityUnshareView",               "activity.views.ActivityUnshareView"),
    ("activity/views/ExerciseCancelView.md",                "ExerciseCancelView",                "activity.views.ExerciseCancelView"),
    ("activity/views/ExerciseDeleteView.md",                "ExerciseDeleteView",                "activity.views.ExerciseDeleteView"),
    ("activity/views/MultipleChoiceExerciseBaseView.md",    "MultipleChoiceExerciseBaseView",    "activity.views.MultipleChoiceExerciseBaseView"),
    ("activity/views/MultipleChoiceExerciseCreateView.md",  "MultipleChoiceExerciseCreateView",  "activity.views.MultipleChoiceExerciseCreateView"),
    ("activity/views/MultipleChoiceExerciseUpdateView.md",  "MultipleChoiceExerciseUpdateView",  "activity.views.MultipleChoiceExerciseUpdateView"),
    ("activity/views/MultipleChoiceExerciseAddOptionView.md","MultipleChoiceExerciseAddOptionView","activity.views.MultipleChoiceExerciseAddOptionView"),
    ("activity/views/CodeExerciseBaseView.md",              "CodeExerciseBaseView",              "activity.views.CodeExerciseBaseView"),
    ("activity/views/CodeExerciseCreateView.md",            "CodeExerciseCreateView",            "activity.views.CodeExerciseCreateView"),
    ("activity/views/CodeExerciseUpdateView.md",            "CodeExerciseUpdateView",            "activity.views.CodeExerciseUpdateView"),
    ("activity/views/CompleteCodeExerciseBaseView.md",      "CompleteCodeExerciseBaseView",      "activity.views.CompleteCodeExerciseBaseView"),
    ("activity/views/CompleteCodeExerciseCreateView.md",    "CompleteCodeExerciseCreateView",    "activity.views.CompleteCodeExerciseCreateView"),
    ("activity/views/CompleteCodeExerciseUpdateView.md",    "CompleteCodeExerciseUpdateView",    "activity.views.CompleteCodeExerciseUpdateView"),
    ("activity/views/DiscursiveExerciseBaseView.md",        "DiscursiveExerciseBaseView",        "activity.views.DiscursiveExerciseBaseView"),
    ("activity/views/DiscursiveExerciseCreateView.md",      "DiscursiveExerciseCreateView",      "activity.views.DiscursiveExerciseCreateView"),
    ("activity/views/DiscursiveExerciseUpdateView.md",      "DiscursiveExerciseUpdateView",      "activity.views.DiscursiveExerciseUpdateView"),
    # activity / forms
    ("activity/forms/ActivityListForm.md",            "ActivityListForm",            "activity.forms.activity.ActivityListForm"),
    ("activity/forms/ActivityAssignWidget.md",        "ActivityAssignWidget",        "activity.forms.activity.ActivityAssignWidget"),
    ("activity/forms/ActivityAssignForm.md",          "ActivityAssignForm",          "activity.forms.activity.ActivityAssignForm"),
    ("activity/forms/ActivityListGroupPeriodForm.md", "ActivityListGroupPeriodForm", "activity.forms.activity.ActivityListGroupPeriodForm"),
    ("activity/forms/SyntaxValidator.md",             "SyntaxValidator",             "activity.forms.exercise.SyntaxValidator"),
    ("activity/forms/ExerciseForm.md",                "ExerciseForm",                "activity.forms.exercise.ExerciseForm"),
    ("activity/forms/CodeExerciseForm.md",            "CodeExerciseForm",            "activity.forms.exercise.CodeExerciseForm"),
    ("activity/forms/CompleteCodeExerciseForm.md",    "CompleteCodeExerciseForm",    "activity.forms.exercise.CompleteCodeExerciseForm"),
    ("activity/forms/DiscursiveExerciseForm.md",      "DiscursiveExerciseForm",      "activity.forms.exercise.DiscursiveExerciseForm"),
    ("activity/forms/ExerciseOptionForm.md",          "ExerciseOptionForm",          "activity.forms.exercise.ExerciseOptionForm"),
    ("activity/forms/BaseExerciseOptionFormSet.md",   "BaseExerciseOptionFormSet",   "activity.forms.formsets.exercise_option.BaseExerciseOptionFormSet"),
    # activity / mixins
    ("activity/mixins/ExerciseBaseMixin.md", "ExerciseBaseMixin", "activity.mixins.ExerciseBaseMixin"),
    # group / models
    ("group/models/generate_group_invite_token.md", "generate_group_invite_token", "group.models.generate_group_invite_token"),
    ("group/models/Group.md",         "Group",         "group.models.Group"),
    ("group/models/GroupArchived.md", "GroupArchived", "group.models.GroupArchived"),
    ("group/models/GroupSharing.md",  "GroupSharing",  "group.models.GroupSharing"),
    ("group/models/GroupStudent.md",  "GroupStudent",  "group.models.GroupStudent"),
    ("group/models/GroupInvite.md",   "GroupInvite",   "group.models.GroupInvite"),
    # group / views
    ("group/views/GroupListBaseView.md",       "GroupListBaseView",       "group.views.GroupListBaseView"),
    ("group/views/GroupActiveListView.md",     "GroupActiveListView",     "group.views.GroupActiveListView"),
    ("group/views/GroupArchivedListView.md",   "GroupArchivedListView",   "group.views.GroupArchivedListView"),
    ("group/views/GroupSharedListView.md",     "GroupSharedListView",     "group.views.GroupSharedListView"),
    ("group/views/GroupCreateOrUpdateView.md", "GroupCreateOrUpdateView", "group.views.GroupCreateOrUpdateView"),
    ("group/views/GroupCreateView.md",         "GroupCreateView",         "group.views.GroupCreateView"),
    ("group/views/GroupUpdateView.md",         "GroupUpdateView",         "group.views.GroupUpdateView"),
    ("group/views/GroupBaseView.md",           "GroupBaseView",           "group.views.GroupBaseView"),
    ("group/views/GroupDetailView.md",         "GroupDetailView",         "group.views.GroupDetailView"),
    ("group/views/GroupShareView.md",          "GroupShareView",          "group.views.GroupShareView"),
    ("group/views/GroupManageArchivingView.md","GroupManageArchivingView","group.views.GroupManageArchivingView"),
    ("group/views/GroupSoftDeleteView.md",     "GroupSoftDeleteView",     "group.views.GroupSoftDeleteView"),
    ("group/views/GroupUnshareView.md",        "GroupUnshareView",        "group.views.GroupUnshareView"),
    ("group/views/GroupInviteCreateView.md",   "GroupInviteCreateView",   "group.views.GroupInviteCreateView"),
    ("group/views/GroupInviteExpireView.md",   "GroupInviteExpireView",   "group.views.GroupInviteExpireView"),
    ("group/views/GroupInviteConfirmView.md",  "GroupInviteConfirmView",  "group.views.GroupInviteConfirmView"),
    # group / forms
    ("group/forms/GroupForm.md",          "GroupForm",          "group.forms.group.GroupForm"),
    ("group/forms/GroupSharingWidget.md", "GroupSharingWidget", "group.forms.group.GroupSharingWidget"),
    ("group/forms/GroupSharingForm.md",   "GroupSharingForm",   "group.forms.group.GroupSharingForm"),
    # common / generic
    ("common/generic/EnhancedListView.md", "EnhancedListView", "common.view.generic.EnhancedListView"),
    # common / mixins
    ("common/mixins/AuthPermissionMixin.md",       "AuthPermissionMixin",       "common.mixins.AuthPermissionMixin"),
    ("common/mixins/HTMXLoginRequiredMixin.md",    "HTMXLoginRequiredMixin",    "common.mixins.HTMXLoginRequiredMixin"),
    ("common/mixins/ObjectAccessRequiredMixin.md", "ObjectAccessRequiredMixin", "common.mixins.ObjectAccessRequiredMixin"),
    ("common/mixins/NavigationMixin.md",           "NavigationMixin",           "common.mixins.NavigationMixin"),
    ("common/mixins/FilteringMixin.md",            "FilteringMixin",            "common.mixins.FilteringMixin"),
    ("common/mixins/OrderingMixin.md",             "OrderingMixin",             "common.mixins.OrderingMixin"),
    ("common/mixins/ViewTypeMixin.md",             "ViewTypeMixin",             "common.mixins.ViewTypeMixin"),
    ("common/mixins/PaginationMixin.md",           "PaginationMixin",           "common.mixins.PaginationMixin"),
    ("common/mixins/EnrichObjectMixin.md",         "EnrichObjectMixin",         "common.mixins.EnrichObjectMixin"),
    ("common/mixins/ActionsMixin.md",              "ActionsMixin",              "common.mixins.ActionsMixin"),
    ("common/mixins/SecondaryFormMixin.md",        "SecondaryFormMixin",        "common.mixins.SecondaryFormMixin"),
    ("common/mixins/InlineFormsetMixin.md",        "InlineFormsetMixin",        "common.mixins.InlineFormsetMixin"),
    # common / views
    ("common/views/LandingPage.md",       "LandingPage",       "common.views.LandingPage"),
    ("common/views/HomeView.md",          "HomeView",          "common.views.HomeView"),
    ("common/views/permission_denied.md", "permission_denied", "common.views.permission_denied"),
    ("common/views/page_not_found.md",    "page_not_found",    "common.views.page_not_found"),
    # common / utils
    ("common/utils/get_btn_action.md", "get_btn_action", "common.utils.get_btn_action"),
    # common / filters
    ("common/filters/get_attr.md",               "get_attr",               "common.templatetags.common_filters.get_attr"),
    ("common/filters/get_attr_with_truncate.md", "get_attr_with_truncate", "common.templatetags.common_filters.get_attr_with_truncate"),
    ("common/filters/get_model_only_fields.md",  "get_model_only_fields",  "common.templatetags.common_filters.get_model_only_fields"),
    ("common/filters/get_item.md",               "get_item",               "common.templatetags.common_filters.get_item"),
    # student / views
    ("student/views/StudentDashboardView.md",   "StudentDashboardView",   "student.views.StudentDashboardView"),
    ("student/views/StudentGroupDetailView.md", "StudentGroupDetailView", "student.views.StudentGroupDetailView"),
]

created = 0
for rel_path, title, directive in pages:
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n::: {directive}\n")
    created += 1

print(f"Criados {created} arquivos.")
