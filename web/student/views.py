"""Views do app student."""
from __future__ import annotations

import difflib
from typing import Any

from activity.models import ActivityListGroup, Exercise, ExerciseOption
from activity.utils import normalize_code
from common.mixins import AuthPermissionMixin
from django.db.models import Count, Max, Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from group.models import Group, GroupSharing, GroupStudent
from student.models import CodeExecution, ExerciseAnswer, Submission


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
        """Retorna as atividades da turma com status e tentativas anotados."""
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
        if not links:
            return links

        now = timezone.now()
        for link in links:
            if link.starts_at and link.starts_at > now:
                status_key = 'future'
            elif link.ends_at and link.ends_at < now:
                status_key = 'closed'
            else:
                status_key = 'open'
            link.status_class, link.status_label = self.STATUS_LABELS[status_key]

        link_ids = [link.pk for link in links]

        # In-progress (unsubmitted) submission per link
        in_progress = {
            s.activity_link_id: s
            for s in Submission.objects.filter(
                student=self.request.user,
                activity_link_id__in=link_ids,
                submitted_at__isnull=True,
            )
        }

        # Latest submitted submission per link (ordered by attempt_number desc)
        latest_submitted: dict[int, Submission] = {}
        for s in Submission.objects.filter(
            student=self.request.user,
            activity_link_id__in=link_ids,
            submitted_at__isnull=False,
        ).order_by('activity_link_id', '-attempt_number'):
            if s.activity_link_id not in latest_submitted:
                latest_submitted[s.activity_link_id] = s

        # Latest INTENTIONAL submission per link (not abandoned — for limited activities)
        latest_intentional: dict[int, Submission] = {}
        for s in Submission.objects.filter(
            student=self.request.user,
            activity_link_id__in=link_ids,
            submitted_at__isnull=False,
            is_abandoned=False,
        ).order_by('activity_link_id', '-attempt_number'):
            if s.activity_link_id not in latest_intentional:
                latest_intentional[s.activity_link_id] = s

        # Opção A: conta só entregues (para atividades ilimitadas)
        submitted_counts: dict[int, int] = dict(
            Submission.objects.filter(
                student=self.request.user,
                activity_link_id__in=link_ids,
                submitted_at__isnull=False,
            ).values('activity_link_id').annotate(n=Count('id')).values_list('activity_link_id', 'n')
        )
        # Conta todas as submissões (cada início de tentativa, incluindo abandonadas pelo beacon)
        all_counts: dict[int, int] = dict(
            Submission.objects.filter(
                student=self.request.user,
                activity_link_id__in=link_ids,
            ).values('activity_link_id').annotate(n=Count('id')).values_list('activity_link_id', 'n')
        )

        activity_list_ids = [link.activity_list_id for link in links]
        exercise_count_by_list = {
            row['activity_list_id']: row['total']
            for row in Exercise.objects
            .filter(activity_list_id__in=activity_list_ids, is_annulled=False)
            .values('activity_list_id')
            .annotate(total=Count('pk'))
        }

        for link in links:
            link.exercise_count = exercise_count_by_list.get(link.activity_list_id, 0)
            max_att = link.activity_list.max_attempts
            # "Continuar" only for truly unlimited activities (no max_attempts AND no ends_at).
            # Any activity with a time deadline or attempt limit uses beacon to close
            # in-progress on leave, so "Iniciar" always reuses existing in-progress silently.
            is_free_unlimited = max_att is None and link.ends_at is None
            link.in_progress_submission = in_progress.get(link.pk) if is_free_unlimited else None
            # For limited activities "latest_submission" means only intentional deliveries.
            # The pending/completed split depends on this: only an intentional submission
            # moves an activity to "completed".
            link.latest_submission = (
                latest_intentional.get(link.pk) if max_att is not None
                else latest_submitted.get(link.pk)
            )
            link.attempts_used = (
                all_counts.get(link.pk, 0) if max_att is not None
                else submitted_counts.get(link.pk, 0)
            )
            has_intentional = latest_intentional.get(link.pk) is not None
            link.can_retry = (
                link.status_class == 'open'
                and not has_intentional
                and (max_att is None or link.attempts_used < max_att)
            )
            link.attempts_exhausted = (
                max_att is not None
                and not has_intentional
                and link.attempts_used >= max_att
            )

        return links

    def _annotate_scores(self, completed_links: list) -> None:
        """Anota pontuação e contagem de acertos em cada atividade concluída."""
        from decimal import Decimal
        from django.db.models import Case, DecimalField, IntegerField, Sum, When

        sub_pks = [l.latest_submission.pk for l in completed_links if l.latest_submission]
        if not sub_pks:
            return

        rows = (
            ExerciseAnswer.objects
            .filter(submission_id__in=sub_pks, exercise__is_annulled=False)
            .values('submission_id')
            .annotate(
                total=Count('id'),
                correct=Sum(Case(When(is_correct=True, then=1), default=0, output_field=IntegerField())),
                pending=Sum(Case(When(is_correct=None, then=1), default=0, output_field=IntegerField())),
                points_earned=Sum(
                    Case(When(is_correct=True, then='exercise__points'), default=Decimal(0), output_field=DecimalField())
                ),
                points_total=Sum('exercise__points', output_field=DecimalField()),
            )
        )
        scores = {r['submission_id']: r for r in rows}
        for link in completed_links:
            if link.latest_submission:
                s = scores.get(link.latest_submission.pk, {
                    'total': 0, 'correct': 0, 'pending': 0,
                    'points_earned': Decimal(0), 'points_total': Decimal(0),
                })
                link.score_total = s['total']
                link.score_correct = s['correct']
                link.score_pending = s['pending']
                link.score_pct = round(s['correct'] / s['total'] * 100) if s['total'] else None
                link.score_points_earned = s['points_earned'] or Decimal(0)
                link.score_points_total = s['points_total'] or Decimal(0)

    def get_context_data(self, **kwargs: Any) -> dict:
        """Monta o contexto da página de detalhes da turma do aluno.

        Returns:
            Dicionário com ``enrollment``, ``group``, ``activity_links``,
            ``pending_links`` e ``completed_links`` (com pontuação anotada).
        """
        context = super().get_context_data(**kwargs)
        enrollment = self.get_enrollment()
        activity_links = self.get_activity_links(enrollment.group)
        pending_links = [
            l for l in activity_links
            if l.in_progress_submission is not None or l.latest_submission is None
        ]
        completed_links = [
            l for l in activity_links
            if l.latest_submission is not None and l.in_progress_submission is None
        ]
        self._annotate_scores(completed_links)
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
    kwargs: dict[str, Any]
    request: HttpRequest

    def get_activity_link(self) -> ActivityListGroup:
        """Carrega o vínculo atividade↔turma e verifica que o aluno está matriculado.

        Raises:
            Http404: Se o vínculo não existir, a atividade estiver deletada ou
                o aluno não estiver matriculado na turma.
        """
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

    def _check_window(self, link: ActivityListGroup) -> HttpResponse | None:
        """Valida a janela temporal da atividade.

        Returns:
            ``HttpResponseRedirect`` com mensagem de erro se a atividade ainda
            não iniciou ou já encerrou; ``None`` se o acesso é permitido.
        """
        now = timezone.now()
        if link.starts_at and now < link.starts_at:
            messages.error(self.request, 'Esta atividade ainda não está disponível.')
            return redirect('student:group_detail', pk=link.group.pk)
        if link.ends_at and now > link.ends_at:
            messages.error(self.request, 'O prazo desta atividade foi encerrado.')
            return redirect('student:group_detail', pk=link.group.pk)
        return None


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

    def _get_or_create_submission(self, activity_link: ActivityListGroup) -> Submission | None:
        """Retorna a tentativa em andamento, cria nova se permitido, ou None se bloqueado."""
        submission = Submission.objects.filter(
            student=self.request.user,
            activity_link=activity_link,
            submitted_at__isnull=True,
        ).first()
        if submission is None:
            max_att = activity_link.activity_list.max_attempts
            if max_att is not None:
                if Submission.objects.filter(
                    student=self.request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                    is_abandoned=False,
                ).exists():
                    return None
                attempts_used = Submission.objects.filter(
                    student=self.request.user,
                    activity_link=activity_link,
                ).count()
            else:
                attempts_used = Submission.objects.filter(
                    student=self.request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                ).count()
            if max_att is not None and attempts_used >= max_att:
                return None
            # Use max existing attempt_number + 1 to avoid unique constraint collisions
            last_num = (
                Submission.objects.filter(
                    student=self.request.user,
                    activity_link=activity_link,
                ).aggregate(n=Max('attempt_number'))['n'] or 0
            )
            submission = Submission.objects.create(
                student=self.request.user,
                activity_link=activity_link,
                attempt_number=last_num + 1,
            )
        return submission

    def _build_exercises(
        self, activity_link: ActivityListGroup
    ) -> list[Exercise]:
        """Retorna exercícios não anulados da atividade com todos os ``select_related`` e prefetch."""
        return list(
            activity_link.activity_list.exercises
            .filter(is_annulled=False)
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
        """Monta o contexto de navegação da atividade (exercícios, respostas, progresso).

        Anota cada exercício com ``is_answered``, ``answer``, ``is_current`` e
        ``nav_index``. Determina o exercício atual por ``navigate_to_pk`` (ou o
        primeiro se não informado) e calcula o percentual de progresso.

        Args:
            activity_link: Vínculo atividade↔turma em uso.
            submission: Tentativa em andamento do aluno.
            navigate_to_pk: ``pk`` do exercício a exibir; usa o primeiro se ``None``.

        Returns:
            Dicionário pronto para o template de resolução de atividade.
        """
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
        """Persiste ou remove a resposta do aluno para um exercício da submissão.

        Para ``multiple_choice``: valida a opção e preenche ``is_correct`` automaticamente.
        Para ``complete_code``: compara código normalizado com o gabarito.
        Para ``code``: aproveita o resultado da última execução se o código bater.
        Para demais tipos: salva o texto sem correção automática.
        Remove o registro se não houver conteúdo (sem opção, sem texto e sem observação).
        """
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
        elif exercise.type == 'complete_code':
            answer_text = post_data.get('answer_text', '').strip()
            defaults['answer_text'] = answer_text
            if answer_text and hasattr(exercise, 'complete_code_exercise'):
                cc = exercise.complete_code_exercise
                defaults['is_correct'] = (
                    normalize_code(answer_text, cc.language)
                    == normalize_code(cc.complete_code, cc.language)
                )
        elif exercise.type == 'code':
            answer_text = post_data.get('answer_text', '').strip()
            defaults['answer_text'] = answer_text
            latest_exec = CodeExecution.objects.filter(
                submission=submission, exercise=exercise,
            ).order_by('-created_at').first()
            if latest_exec and latest_exec.source_code.strip() == answer_text:
                defaults['is_correct'] = latest_exec.all_correct
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
        """Carrega ou cria a submissão e renderiza a página de resolução.

        Para atividades com limite de tentativas, bloqueia o acesso após entrega
        intencional ou esgotamento de tentativas. Detecta ``HX-Request`` para
        retornar apenas o fragmento ``_activity_main.html``.
        """
        activity_link = self.get_activity_link()

        block = self._check_window(activity_link)
        if block:
            return block

        max_att = activity_link.activity_list.max_attempts

        if max_att is not None:
            # Reconnect reuses the in-progress attempt — the beacon (pagehide) closes it
            # only when the student intentionally leaves (refresh, back button, close tab).
            # A genuine network drop won't fire the beacon, so the attempt survives and
            # the student can pick up where they left off at no extra cost.
            submission = Submission.objects.filter(
                student=request.user,
                activity_link=activity_link,
                submitted_at__isnull=True,
            ).first()

            if submission is None:
                # Block once the student has intentionally submitted
                has_intentional = Submission.objects.filter(
                    student=request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                    is_abandoned=False,
                ).exists()
                if has_intentional:
                    messages.info(request, 'Você já entregou esta atividade.')
                    return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])

                # Each submission created = 1 attempt consumed (beacon-closed or submitted)
                attempts_used = Submission.objects.filter(
                    student=request.user,
                    activity_link=activity_link,
                ).count()
                if attempts_used >= max_att:
                    messages.error(
                        request,
                        f'Você já utilizou tod{"a" if max_att == 1 else "as"} as {max_att} '
                        f'tentativa{"" if max_att == 1 else "s"} disponíve{"l" if max_att == 1 else "is"}.',
                    )
                    return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])
                last_num = (
                    Submission.objects.filter(
                        student=request.user,
                        activity_link=activity_link,
                    ).aggregate(n=Max('attempt_number'))['n'] or 0
                )
                submission = Submission.objects.create(
                    student=request.user,
                    activity_link=activity_link,
                    attempt_number=last_num + 1,
                )
        else:
            submission = Submission.objects.filter(
                student=request.user,
                activity_link=activity_link,
                submitted_at__isnull=True,
            ).first()
            if submission is None:
                has_intentional = Submission.objects.filter(
                    student=request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                    is_abandoned=False,
                ).exists()
                if has_intentional:
                    messages.info(request, 'Você já entregou esta atividade.')
                    return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])
                attempts_used = Submission.objects.filter(
                    student=request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                    is_abandoned=False,
                ).count()
                last_num = (
                    Submission.objects.filter(
                        student=request.user,
                        activity_link=activity_link,
                    ).aggregate(n=Max('attempt_number'))['n'] or 0
                )
                submission = Submission.objects.create(
                    student=request.user,
                    activity_link=activity_link,
                    attempt_number=last_num + 1,
                )

        navigate_to_str = request.GET.get('exercise', '')
        navigate_to_pk = int(navigate_to_str) if navigate_to_str.isdigit() else None

        context = self._build_context(activity_link, submission, navigate_to_pk)

        if request.headers.get('HX-Request'):
            return render(request, 'student/partials/_activity_main.html', context)
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Salva a resposta do exercício atual e navega para o próximo ou para a revisão.

        ``go_review=1`` no POST redireciona para a tela de revisão (suporte a HTMX via
        ``HX-Redirect``). Caso contrário, renderiza o fragmento ou a página completa
        no exercício indicado por ``navigate_to_pk``.
        """
        activity_link = self.get_activity_link()

        block = self._check_window(activity_link)
        if block:
            return block

        submission = self._get_or_create_submission(activity_link)

        if submission is None or submission.submitted_at:
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


class StudentAbandonView(_ActivityAccessMixin, View):
    """Fecha a tentativa em andamento quando o aluno sai da atividade sem submeter.

    Chamado via navigator.sendBeacon no evento pagehide do navegador.
    Age em qualquer atividade que tenha prazo (ends_at) ou limite de tentativas.
    Atividades sem prazo e sem limite não disparam o beacon.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        activity_link = self.get_activity_link()
        has_constraint = (
            activity_link.activity_list.max_attempts is not None
            or activity_link.ends_at is not None
        )
        if has_constraint:
            Submission.objects.filter(
                student=request.user,
                activity_link=activity_link,
                submitted_at__isnull=True,
            ).update(submitted_at=timezone.now(), is_abandoned=True)
        return HttpResponse(status=204)


class StudentActivityReviewView(_ActivityAccessMixin, TemplateView):
    """Tela de revisão das respostas antes da submissão final.

    Exibe todos os exercícios com as respostas do aluno sem indicadores de
    acerto/erro. Alerta sobre exercícios sem resposta e permite ao aluno
    voltar para editar ou confirmar a entrega.
    """

    template_name = 'student/activity_review.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Valida janela e submissão em andamento antes de renderizar a revisão.

        Redireciona para a resolução se não houver submissão em andamento.
        Armazena ``activity_link`` e ``submission`` em atributos de instância
        para uso em :meth:`get_context_data`.
        """
        activity_link = self.get_activity_link()

        block = self._check_window(activity_link)
        if block:
            return block

        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
            submitted_at__isnull=True,
        ).first()

        if not submission:
            return redirect('student:activity', link_pk=self.kwargs['link_pk'])

        self._activity_link = activity_link
        self._submission = submission
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        """Adiciona exercícios com respostas anotadas e contagem de não respondidos."""
        context = super().get_context_data(**kwargs)
        activity_link = self._activity_link
        submission = self._submission

        exercises = list(
            activity_link.activity_list.exercises
            .filter(is_annulled=False)
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
    """Verifica que o usuário é o dono da turma do ActivityListGroup ou tem compartilhamento ativo."""
    kwargs: dict[str, Any]
    request: HttpRequest

    def get_activity_link(self) -> ActivityListGroup:
        """Carrega o vínculo e valida que o usuário é o professor responsável.

        Aceita o criador da turma ou professores com compartilhamento ativo.

        Raises:
            Http404: Se o vínculo não existir ou o usuário não tiver acesso.
        """
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

        # Only intentionally delivered submissions (excludes abandoned/in-progress)
        raw_submitted = (
            Submission.objects.filter(
                activity_link=activity_link,
                submitted_at__isnull=False,
                is_abandoned=False,
            )
            .select_related('student')
            .order_by('submitted_at')
        )

        # Deduplicate by student: keep only the highest attempt_number per student
        # (handles legacy data where multiple submissions may share is_abandoned=False)
        _seen: dict[int, Any] = {}
        for sub in raw_submitted:
            if sub.student_id not in _seen or sub.attempt_number > _seen[sub.student_id].attempt_number:
                _seen[sub.student_id] = sub
        submitted = sorted(_seen.values(), key=lambda s: s.submitted_at)

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

        submissions_to_grade = [s for s in submitted if s.pending_count > 0 or s.answered_count < total_exercises]
        submissions_graded = [s for s in submitted if s.pending_count == 0 and s.answered_count >= total_exercises]

        context.update({
            'activity_link': activity_link,
            'submissions': submitted,
            'submissions_to_grade': submissions_to_grade,
            'submissions_graded': submissions_graded,
            'pending_enrollments': pending_enrollments,
            'total_exercises': total_exercises,
            'total_enrolled': len(submitted) + len(pending_enrollments),
            'in_progress_count': sum(1 for e in pending_enrollments if e.in_progress),
        })
        return context


class TeacherGradeView(_TeacherAccessMixin, View):
    """Correção manual de uma submissão pelo professor.

    Salva acerto/erro por questão, comentário por questão e comentário geral.
    """

    template_name = 'student/teacher_grade.html'

    @staticmethod
    def _compute_exec_diff(prev: str, curr: str) -> list[dict]:
        """Diff linha a linha entre duas versões de código (para o painel de timeline)."""
        prev_lines = prev.splitlines()
        curr_lines = curr.splitlines()
        lines: list[dict] = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, prev_lines, curr_lines).get_opcodes():
            if tag == 'equal':
                for k in range(i2 - i1):
                    lines.append({'t': 'ctx', 'ol': i1 + k + 1, 'nl': j1 + k + 1, 'c': prev_lines[i1 + k]})
            elif tag in ('replace', 'delete'):
                for k in range(i2 - i1):
                    lines.append({'t': 'rem', 'ol': i1 + k + 1, 'nl': '', 'c': prev_lines[i1 + k]})
                if tag == 'replace':
                    for k in range(j2 - j1):
                        lines.append({'t': 'add', 'ol': '', 'nl': j1 + k + 1, 'c': curr_lines[j1 + k]})
            elif tag == 'insert':
                for k in range(j2 - j1):
                    lines.append({'t': 'add', 'ol': '', 'nl': j1 + k + 1, 'c': curr_lines[j1 + k]})
        return lines

    def _get_submission(self, activity_link: ActivityListGroup) -> Submission:
        """Retorna a submissão entregue para correção ou levanta 404.

        Raises:
            Http404: Se a submissão não existir ou ainda não tiver sido entregue.
        """
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
        """Retorna o contexto com exercícios e respostas do aluno para a tela de correção."""
        exercises = list(
            activity_link.activity_list.exercises
            .filter(is_annulled=False)
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

        execs_by_exercise: dict[int, list] = {}
        for ce in submission.code_executions.order_by('created_at'):
            execs_by_exercise.setdefault(ce.exercise_id, []).append(ce)

        for ex in exercises:
            ex.answer = answers.get(ex.pk)
            execs = execs_by_exercise.get(ex.pk, [])
            for i, ce in enumerate(execs):
                ce.exec_num = i + 1
                ce.is_baseline = i == 0
                ce.diff = None if i == 0 else self._compute_exec_diff(execs[i - 1].source_code, ce.source_code)
            ex.code_executions_list = execs

        return {
            'activity_link': activity_link,
            'submission': submission,
            'exercises': exercises,
        }

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Renderiza o formulário de correção manual da submissão."""
        activity_link = self.get_activity_link()
        submission = self._get_submission(activity_link)
        return render(request, self.template_name, self._build_context(activity_link, submission))

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Aplica acerto/erro por questão e comentários, depois redireciona para a lista de submissões."""
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


class StudentExercisePingView(_ActivityAccessMixin, View):
    """Registra a chegada do aluno em um slide de exercício.

    Fecha o timer do exercício anterior (acumulando segundos em
    :attr:`~student.models.ExerciseAnswer.time_spent_seconds`) e abre o
    timer do novo. O cliente nunca envia um valor de tempo — apenas informa
    o pk do exercício em que chegou; o servidor calcula o elapsed com seus
    próprios timestamps de sessão.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Processa o ping de chegada e atualiza o timer acumulado do exercício anterior."""
        exercise_pk = request.POST.get('exercise_pk')
        if not exercise_pk:
            return HttpResponse(status=400)

        try:
            exercise_pk = int(exercise_pk)
        except ValueError:
            return HttpResponse(status=400)

        activity_link = self.get_activity_link()
        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
            submitted_at__isnull=True,
        ).first()

        if not submission:
            return HttpResponse(status=204)

        self._close_and_open(request, activity_link.pk, submission, exercise_pk)
        return HttpResponse(status=204)

    @staticmethod
    def _close_and_open(
        request: HttpRequest,
        link_pk: int,
        submission: 'Submission',
        new_exercise_pk: int,
    ) -> None:
        """Fecha o timer do exercício anterior e abre o do novo.

        Reutilizado por :class:`StudentSubmitView` para fechar o último timer.
        """
        from django.db.models import F

        session_key = f'exercise_timer_{link_pk}'
        now = timezone.now()
        prev = request.session.get(session_key)

        if prev and prev.get('exercise_pk') != new_exercise_pk:
            try:
                entered_at = timezone.datetime.fromisoformat(prev['entered_at'])
                elapsed = int((now - entered_at).total_seconds())
                if elapsed > 0:
                    ExerciseAnswer.objects.filter(
                        submission=submission,
                        exercise_id=prev['exercise_pk'],
                    ).update(time_spent_seconds=F('time_spent_seconds') + elapsed)
            except (KeyError, ValueError, TypeError):
                pass

        request.session[session_key] = {
            'exercise_pk': new_exercise_pk,
            'entered_at': now.isoformat(),
        }


class StudentSubmitView(_ActivityAccessMixin, View):
    """Submissão final de uma atividade pelo aluno.

    Marca ``submitted_at`` na Submission e redireciona para os resultados.
    Idempotente: se já submetido, apenas redireciona.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Finaliza a submissão, dispara autocorreção quando aplicável e redireciona para os resultados."""
        activity_link = self.get_activity_link()

        block = self._check_window(activity_link)
        if block:
            return block

        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
            submitted_at__isnull=True,
        ).first()

        if not submission:
            raise Http404

        self._close_last_timer(request, activity_link, submission)

        if not activity_link.activity_list.manual_grading:
            self._auto_grade(submission)

        submission.submitted_at = timezone.now()
        submission.save(update_fields=['submitted_at'])

        return redirect('student:activity_result', link_pk=self.kwargs['link_pk'])

    def _close_last_timer(
        self,
        request: HttpRequest,
        activity_link: ActivityListGroup,
        submission: Submission,
    ) -> None:
        """Fecha o timer do último exercício ativo antes da entrega."""
        session_key = f'exercise_timer_{activity_link.pk}'
        prev = request.session.pop(session_key, None)
        if not prev:
            return
        try:
            from django.db.models import F
            entered_at = timezone.datetime.fromisoformat(prev['entered_at'])
            elapsed = int((timezone.now() - entered_at).total_seconds())
            if elapsed > 0:
                ExerciseAnswer.objects.filter(
                    submission=submission,
                    exercise_id=prev['exercise_pk'],
                ).update(time_spent_seconds=F('time_spent_seconds') + elapsed)
        except (KeyError, ValueError, TypeError):
            pass

    def _auto_grade(self, submission: Submission) -> None:
        """Dispara correção automática para exercícios de código (via Celery) e código completo.

        Exercícios do tipo ``code`` são enfileirados como tarefa assíncrona.
        Exercícios ``complete_code`` são corrigidos de forma síncrona por
        comparação de código normalizado. Outros tipos são ignorados.
        """
        from activity.utils import normalize_code
        from student.tasks import execute_code_task

        answers = (
            ExerciseAnswer.objects
            .filter(submission=submission)
            .select_related(
                'exercise',
                'exercise__code_exercise',
                'exercise__complete_code_exercise',
            )
        )

        for answer in answers:
            ex = answer.exercise
            if ex.is_annulled or not answer.answer_text:
                continue

            if ex.type == 'code':
                execute_code_task.delay(submission.pk, ex.pk, answer.answer_text)

            elif ex.type == 'complete_code':
                try:
                    cc = ex.complete_code_exercise
                    answer.is_correct = (
                        normalize_code(answer.answer_text, cc.language)
                        == normalize_code(cc.complete_code, cc.language)
                    )
                    answer.save(update_fields=['is_correct'])
                except Exception:
                    pass


class StudentFeedbackView(_ActivityAccessMixin, View):
    """Salva o feedback geral do aluno sobre a atividade após submissão."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Persiste ``student_feedback`` na submissão mais recente e redireciona para a turma."""
        activity_link = self.get_activity_link()
        max_att = activity_link.activity_list.max_attempts

        qs = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
            submitted_at__isnull=False,
        )
        if max_att is not None:
            qs = qs.filter(is_abandoned=False)
        submission = qs.order_by('-attempt_number').first()

        if not submission:
            raise Http404

        submission.student_feedback = request.POST.get('student_feedback', '').strip()
        submission.save(update_fields=['student_feedback'])

        return redirect('student:group_detail', pk=activity_link.group.pk)


class StudentResultView(_ActivityAccessMixin, TemplateView):
    """Resultados de uma atividade submetida pelo aluno."""

    template_name = 'student/result.html'

    def get_activity_link(self) -> ActivityListGroup:
        """Carrega o vínculo sem filtrar atividades deletadas, permitindo ver resultados de atividades removidas.

        Levanta 404 se o aluno não estiver matriculado ou se a atividade foi deletada
        sem que o aluno tenha ao menos uma submissão entregue.

        Raises:
            Http404: Sem acesso ou sem submissão para atividade deletada.
        """
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
        """Carrega a submissão a exibir e redireciona para resolução se ainda não houver entrega.

        Para atividades com limite de tentativas, prioriza a submissão intencional
        mais recente; usa a última submetida como fallback. Armazena referências em
        atributos de instância para :meth:`get_context_data`.
        """
        activity_link = self.get_activity_link()
        max_att = activity_link.activity_list.max_attempts

        if max_att is not None:
            # For limited activities, prefer the intentional submission
            submission = (
                Submission.objects
                .filter(
                    student=request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                    is_abandoned=False,
                )
                .order_by('-attempt_number')
                .first()
            )
            # Fallback: student used all attempts without intentional submit
            if not submission:
                submission = (
                    Submission.objects
                    .filter(
                        student=request.user,
                        activity_link=activity_link,
                        submitted_at__isnull=False,
                    )
                    .order_by('-attempt_number')
                    .first()
                )
        else:
            submission = (
                Submission.objects
                .filter(
                    student=request.user,
                    activity_link=activity_link,
                    submitted_at__isnull=False,
                )
                .order_by('-attempt_number')
                .first()
            )

        if not submission:
            return redirect('student:activity', link_pk=self.kwargs['link_pk'])

        self._activity_link = activity_link
        self._submission = submission
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        """Calcula pontuação, percentual de acerto, tentativas restantes e flag ``can_retry``."""
        context = super().get_context_data(**kwargs)
        activity_link = self._activity_link
        submission = self._submission

        exercises = list(
            activity_link.activity_list.exercises
            .filter(is_annulled=False)
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

        total_points = sum(float(ex.points) for ex in exercises if not ex.is_annulled)
        earned_points = sum(
            float(ex.points)
            for ex in exercises
            if not ex.is_annulled and (a := answers.get(ex.pk)) and a.is_correct
        )
        answered_count = len(answers)
        auto_graded = sum(
            1 for a in answers.values() if a.is_correct is not None
        )
        pending_review = answered_count - auto_graded
        score_pct = round(earned_points / total_points * 100) if total_points else 0

        now = timezone.now()
        window_open = (
            (activity_link.starts_at is None or now >= activity_link.starts_at)
            and (activity_link.ends_at is None or now <= activity_link.ends_at)
        )
        max_att = activity_link.activity_list.max_attempts
        has_intentional = Submission.objects.filter(
            student=submission.student,
            activity_link=activity_link,
            submitted_at__isnull=False,
            is_abandoned=False,
        ).exists()
        if max_att is not None:
            attempts_used = Submission.objects.filter(
                student=submission.student,
                activity_link=activity_link,
            ).count()
            can_retry = window_open and not has_intentional and attempts_used < max_att
            attempts_remaining = max_att - attempts_used
        else:
            attempts_used = Submission.objects.filter(
                student=submission.student,
                activity_link=activity_link,
                submitted_at__isnull=False,
            ).count()
            can_retry = window_open and not has_intentional
            attempts_remaining = None

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
            'attempts_used': attempts_used,
            'max_attempts': max_att,
            'attempts_remaining': attempts_remaining,
            'can_retry': can_retry,
        })
        return context


# ---------------------------------------------------------------------------
# Execução de código (Executar)
# ---------------------------------------------------------------------------

class StudentRunCodeView(_ActivityAccessMixin, View):
    """Enfileira a execução do código do aluno no Celery e retorna polling HTML."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Valida o exercício, verifica limite de execuções e enfileira a tarefa Celery.

        Retorna o fragmento de polling ``_run_code_polling.html`` com a URL de
        verificação de status. Em caso de erro (exercício inválido, código vazio,
        limite atingido) retorna ``_run_code_result.html`` com a mensagem de erro.
        """
        from student.tasks import execute_code_task

        activity_link = self.get_activity_link()

        exercise_pk_str = (
            request.POST.get('exercise_pk') or request.POST.get('current_exercise_pk', '')
        )
        if not exercise_pk_str.isdigit():
            return render(request, 'student/partials/_run_code_result.html',
                          {'error': 'Exercício inválido.'})

        exercise_pk = int(exercise_pk_str)

        try:
            exercise = (
                Exercise.objects
                .select_related('code_exercise', 'complete_code_exercise')
                .get(
                    pk=exercise_pk,
                    activity_list=activity_link.activity_list,
                    type__in=['code', 'complete_code'],
                    is_annulled=False,
                )
            )
        except Exercise.DoesNotExist:
            raise Http404

        submission = Submission.objects.filter(
            student=request.user,
            activity_link=activity_link,
            submitted_at__isnull=True,
            is_abandoned=False,
        ).first()

        if not submission:
            return render(request, 'student/partials/_run_code_result.html', {
                'error': 'Nenhuma tentativa em andamento.',
                'needs_reload': True,
                'exercise_pk': exercise_pk,
            })

        max_exec = (
            exercise.code_exercise.max_executions
            if exercise.type == 'code'
            else None
        )
        if max_exec is not None:
            used = CodeExecution.objects.filter(
                submission=submission, exercise=exercise
            ).count()
            if used >= max_exec:
                return render(request, 'student/partials/_run_code_result.html', {
                    'error': f'Limite de {max_exec} execuções atingido para este exercício.',
                    'exercise_pk': exercise_pk,
                })

        source_code = (
            request.POST.get('source_code') or request.POST.get('answer_text', '')
        ).strip()
        if not source_code:
            return render(request, 'student/partials/_run_code_result.html', {
                'error': 'O código não pode estar vazio.',
                'exercise_pk': exercise_pk,
            })

        task = execute_code_task.delay(submission.pk, exercise.pk, source_code)

        poll_url = (
            reverse('student:activity_run_code_poll',
                    kwargs={'link_pk': activity_link.pk, 'task_id': task.id})
            + f'?exercise_pk={exercise_pk}'
        )

        return render(request, 'student/partials/_run_code_polling.html', {
            'exercise_pk': exercise_pk,
            'poll_url': poll_url,
        })


class StudentRunCodePollView(_ActivityAccessMixin, View):
    """Verifica o status da tarefa Celery e retorna resultado ou spinner."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Consulta a tarefa Celery e retorna o fragmento de resultado ou o spinner de espera."""
        from celery.result import AsyncResult

        task_id = self.kwargs['task_id']
        exercise_pk = request.GET.get('exercise_pk', '')
        result = AsyncResult(task_id)

        if not result.ready():
            activity_link = self.get_activity_link()
            poll_url = (
                reverse('student:activity_run_code_poll',
                        kwargs={'link_pk': activity_link.pk, 'task_id': task_id})
                + f'?exercise_pk={exercise_pk}'
            )
            return render(request, 'student/partials/_run_code_polling.html', {
                'exercise_pk': exercise_pk,
                'poll_url': poll_url,
            })

        data = result.get(timeout=1)

        if 'error' in data:
            return render(request, 'student/partials/_run_code_result.html', {
                'error': data['error'],
                'exercise_pk': exercise_pk,
            })

        if data.get('complete_code'):
            return render(request, 'student/partials/_run_code_result.html', {
                'complete_code': True,
                'is_correct': data['is_correct'],
                'exercise_pk': exercise_pk,
            })

        if data.get('run_only'):
            return render(request, 'student/partials/_run_code_result.html', {
                'run_only': True,
                'stdout': data['stdout'],
                'stderr': data['stderr'],
                'status': data['status'],
                'is_correct': data.get('is_correct'),
                'exercise_pk': exercise_pk,
            })

        return render(request, 'student/partials/_run_code_result.html', {
            'results': data['results'],
            'all_correct': data['all_correct'],
            'correct_count': data['correct_count'],
            'total_count': data['total_count'],
            'complete_code': data.get('complete_code', False),
            'exercise_pk': exercise_pk,
        })
