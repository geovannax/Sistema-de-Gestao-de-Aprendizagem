# group

O app **group** gerencia turmas criadas por professores. Uma turma pode ser compartilhada com outros professores, receber alunos via convite por token e ter atividades vinculadas com período de realização opcional. Turmas excluídas usam soft delete.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| models | [Group](models/Group.md), [GroupArchived](models/GroupArchived.md), [GroupSharing](models/GroupSharing.md), [GroupStudent](models/GroupStudent.md), [GroupInvite](models/GroupInvite.md) |
| views | [GroupListBaseView](views/GroupListBaseView.md), [GroupDetailView](views/GroupDetailView.md), [GroupShareView](views/GroupShareView.md), [GroupInviteConfirmView](views/GroupInviteConfirmView.md), e mais |
| forms | [GroupForm](forms/GroupForm.md), [GroupSharingWidget](forms/GroupSharingWidget.md), [GroupSharingForm](forms/GroupSharingForm.md) |
