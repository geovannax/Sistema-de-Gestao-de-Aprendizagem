from django.contrib import admin
from group.models import Group, GroupArchived, GroupInvite, GroupSharing, GroupStudent


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at', 'updated_at', 'deleted_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('name', 'description', 'shift', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    
    fieldsets = (
        ('Informações', {
            'fields': ('name', 'description', 'shift', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GroupSharing)
class GroupSharingAdmin(admin.ModelAdmin):
    list_display = ('get_group', 'shared_with', 'shared_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('group__name', 'shared_with__username', 'shared_by__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Dados', {
            'fields': ('group', 'shared_with', 'shared_by', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_group(self, obj):
        return obj.group.name
    get_group.short_description = 'Grupo'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'group', 'shared_with', 'shared_by'
        )


@admin.register(GroupArchived)
class GroupArchivedAdmin(admin.ModelAdmin):
    list_display = ('get_group', 'user', 'is_archived', 'created_at')
    list_filter = ('is_archived', 'created_at')
    search_fields = ('group__name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Dados', {
            'fields': ('group', 'user', 'is_archived')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_group(self, obj):
        return obj.group.name
    get_group.short_description = 'Grupo'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'user')


@admin.register(GroupStudent)
class GroupStudentAdmin(admin.ModelAdmin):
    list_display = ('get_group', 'student', 'is_active', 'joined_at')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('group__name', 'student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('joined_at', 'updated_at')

    def get_group(self, obj):
        return obj.group.name
    get_group.short_description = 'Grupo'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'student')


@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ('get_group', 'created_by', 'is_active', 'expires_at', 'used_count', 'max_uses')
    list_filter = ('is_active', 'expires_at', 'created_at')
    search_fields = ('group__name', 'created_by__username', 'token')
    readonly_fields = ('token', 'used_count', 'created_at', 'updated_at')

    def get_group(self, obj):
        return obj.group.name
    get_group.short_description = 'Grupo'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'created_by')
