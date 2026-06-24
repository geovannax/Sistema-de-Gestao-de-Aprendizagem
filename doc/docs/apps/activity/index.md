# activity

O app **activity** gerencia listas de atividades e exercícios polimórficos. Uma `ActivityList` agrupa exercícios de quatro tipos distintos, pode ser vinculada a turmas com período de realização e pode ser arquivada sem exclusão do banco de dados.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| constants | [Constantes](constants.md) |
| models | [ActivityList](models/ActivityList.md), [ActivityArchived](models/ActivityArchived.md), [ActivityListGroup](models/ActivityListGroup.md), [Exercise](models/Exercise.md), [CodeExercise](models/CodeExercise.md), [CompleteCodeExercise](models/CompleteCodeExercise.md), [MultipleChoiceExercise](models/MultipleChoiceExercise.md), [ExerciseOption](models/ExerciseOption.md), [DiscursiveExercise](models/DiscursiveExercise.md) |
| views | [ActivityListBaseView](views/ActivityListBaseView.md), [ActivityListView](views/ActivityListView.md), [ActivityCreateView](views/ActivityCreateView.md), [ActivityDetailView](views/ActivityDetailView.md), e mais |
| forms | [ActivityListForm](forms/ActivityListForm.md), [ActivityAssignForm](forms/ActivityAssignForm.md), [ExerciseForm](forms/ExerciseForm.md), e mais |
| mixins | [ExerciseBaseMixin](mixins/ExerciseBaseMixin.md) |
