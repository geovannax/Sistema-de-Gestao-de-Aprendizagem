# student

O app **student** implementa a área do aluno e a interface de correção para professores.

Após aceitar o convite de uma turma, o aluno acessa seu dashboard com as turmas matriculadas, resolve as atividades disponíveis e consulta os resultados. O professor dono da turma acessa a aba **Revisão** para corrigir submissões manualmente.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| models | [Submission](models/Submission.md), [ExerciseAnswer](models/ExerciseAnswer.md), [CodeExecution](models/CodeExecution.md) |
| tasks | [execute_code_task](tasks/execute_code_task.md) |
| views (aluno) | [StudentDashboardView](views/StudentDashboardView.md), [StudentGroupDetailView](views/StudentGroupDetailView.md), [StudentActivityView](views/StudentActivityView.md), [StudentSubmitView](views/StudentSubmitView.md), [StudentResultView](views/StudentResultView.md) |
| views (professor) | [TeacherSubmissionsView](views/TeacherSubmissionsView.md), [TeacherGradeView](views/TeacherGradeView.md) |

## Fluxo do aluno

1. Acessa o dashboard (`StudentDashboardView`) e vê as turmas matriculadas.
2. Entra no detalhe da turma (`StudentGroupDetailView`): atividades divididas em **Pendentes** e **Concluídas**.
3. Clica em **Iniciar** / **Continuar** → `StudentActivityView` (cria ou retoma a `Submission`).
4. Navega entre exercícios via HTMX (POST salva a resposta e retorna o fragmento `_activity_main.html`).
5. Clica em **Entregar** → `StudentSubmitView` (preenche `submitted_at`).
6. Redireciona para `StudentResultView` com pontuação e status de revisão pendente.

## Fluxo do professor

1. Acessa a aba **Revisão** na página da turma (`GroupReviewView` em `group`).
2. Clica em **Corrigir** → `TeacherSubmissionsView`: lista de alunos que entregaram.
3. Clica em uma submissão → `TeacherGradeView`: visualiza e corrige cada resposta.
   - `MULTIPLE_CHOICE`: auto-corrigido (somente leitura).
   - Demais tipos: radio *Correta* / *Incorreta* por exercício.
