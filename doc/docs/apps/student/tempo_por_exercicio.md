# Rastreamento de Tempo por Exercício

O sistema registra quanto tempo cada aluno gasta em cada exercício durante uma atividade. O tempo é acumulado no campo `time_spent_seconds` de [`ExerciseAnswer`](models/ExerciseAnswer.md) e exibido para o professor na tela de correção (`TeacherGradeView`).

---

## Campo de armazenamento

`ExerciseAnswer.time_spent_seconds` — inteiro sem sinal, em segundos, padrão `0`.

O campo é **acumulativo**: cada vez que o aluno retorna a um exercício, o tempo da nova visita é somado ao total existente.

---

## Arquitetura: timestamps no servidor

O tempo **nunca é enviado pelo cliente**. O navegador apenas avisa ao servidor "cheguei neste exercício" (`StudentExercisePingView`). O servidor registra o instante de chegada na sessão Django e calcula o elapsed quando o aluno sai do slide.

Isso torna o mecanismo significativamente mais difícil de manipular do que abordagens baseadas em campos ocultos (onde o aluno poderia editar o valor via DevTools antes de submeter).

---

## Fluxo detalhado

```
Aluno abre atividade
  └─ JS dispara pingView(ex1.pk)
       └─ POST /student/activity/<link_pk>/ping/
            └─ session["exercise_timer_<link>"] = { exercise_pk: ex1, entered_at: T0 }

Aluno navega para exercício 2
  └─ JS dispara pingView(ex2.pk)
       └─ POST /student/activity/<link_pk>/ping/
            ├─ elapsed = now() - T0
            ├─ ExerciseAnswer[ex1].time_spent_seconds += elapsed
            └─ session = { exercise_pk: ex2, entered_at: T1 }

Aluno retorna para exercício 1
  └─ JS dispara pingView(ex1.pk)
       └─ POST /student/activity/<link_pk>/ping/
            ├─ elapsed = now() - T1
            ├─ ExerciseAnswer[ex2].time_spent_seconds += elapsed   ← acumula ex2
            └─ session = { exercise_pk: ex1, entered_at: T2 }

Aluno entrega a atividade
  └─ StudentSubmitView._close_last_timer()
       ├─ elapsed = now() - T2
       ├─ ExerciseAnswer[ex1].time_spent_seconds += elapsed        ← fecha ex1
       └─ session key removida
```

### Resultado para exercício 1

```
time_spent_seconds = (T1 − T0)   +   (T_entrega − T2)
                      1ª visita       retorno
```

---

## Comportamento em cenários específicos

### Retorno a exercícios anteriores

O sistema acumula corretamente. Cada vez que o aluno chega em um slide, o servidor fecha o timer do slide anterior e abre um novo timer para o atual — independentemente da ordem de navegação.

### Execução de código (auto-correção)

O tempo de espera da execução do sandbox **é incluído** no `time_spent_seconds`. Enquanto o Celery processa o código (tipicamente 2–10 s), o aluno permanece no slide e o timer continua. Isso é comportamento intencional: o aluno está ativamente engajado com o exercício durante esse período.

O `update_or_create` do Celery (`execute_code_task`) atualiza apenas `answer_text` e `is_correct` — **`time_spent_seconds` não é tocado** pelo worker de correção, evitando que execuções subsequentes resetem o tempo acumulado.

### Aluno abandona a aba sem entregar

Se o aluno fechar o navegador ou a aba sem entregar, o timer da sessão permanece aberto. O tempo não é contabilizado no `ExerciseAnswer` porque `_close_last_timer` só é chamado em `StudentSubmitView`. Submissões abandonadas (`is_abandoned=True`) têm `time_spent_seconds` parcialmente acumulado até o último ping processado.

### Múltiplas tentativas

Cada `Submission` tem seu próprio conjunto de `ExerciseAnswer`. O `time_spent_seconds` é independente por tentativa — não há acumulação entre tentativas distintas.

---

## Componentes implementados

| Componente | Responsabilidade |
|---|---|
| `ExerciseAnswer.time_spent_seconds` | Armazena o total acumulado em segundos |
| `StudentExercisePingView` | Endpoint `POST /student/activity/<link_pk>/ping/` — fecha timer anterior, abre novo |
| `StudentExercisePingView._close_and_open()` | Lógica de sessão reutilizada pelo submit |
| `StudentSubmitView._close_last_timer()` | Fecha o timer do último exercício ativo na entrega |
| `pingView()` em `activity_detail.html` | Chama o ping ao chegar em cada slide e no carregamento inicial |
| Filtro `duration` em `common_filters` | Formata segundos como `3min 20s`, `1h 5min`, etc. |

---

## Limitações conhecidas

- **Tempo inclui inatividade passiva**: se o aluno abrir o exercício e deixar a aba em segundo plano sem navegar, o timer continua. Não há detecção de foco de aba (`visibilitychange`) no ping — seria possível adicionar pausa/retomada via JS como melhoria futura.
- **Manipulação avançada**: um aluno determinado poderia enviar pings artificiais via `fetch` para qualquer exercício. O endpoint não aplica rate-limit por exercício. Adicionar um intervalo mínimo entre pings (ex.: ignorar pings chegando em menos de 25 s) reduziria esse vetor.
- **Granularidade de 1 segundo**: `elapsed` é calculado com `int()`, arredondando para baixo. Para análises que exijam sub-segundo, seria necessário usar `float` ou `Decimal`.
