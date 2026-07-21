/* ════════════════════════════════════════════════════════════════
   EDUCATRIX — Guided Tour Engine
   ════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Step definitions ─────────────────────────────────────────── */
  var STEPS = [
    {
      n: 1,
      title: 'Criar uma Turma',
      desc: 'Preencha o nome, turno e descrição da turma. Salve para criar — você pode ter quantas quiser.',
      match: function () {
        var phase = state.step1Phase || 0;
        if (/\/group\/active/.test(location.pathname)) {
          if (new URLSearchParams(location.search).get('group_created') === '1' || state.step1GroupCreated) return true;
          if (phase === 1) return true;
          return false;
        }
        if (/\/group\/create\/?$/.test(location.pathname)) return true;
        if (phase === 0) return true;
        return false;
      },
      isReady: function () {
        var phase = state.step1Phase || 0;
        if (phase === 0) return !!document.querySelector('a[href*="/group/active/"]');
        if (phase === 1) return !!document.querySelector('a[href*="/group/create/"]');
        return true;
      },
      resolveSelector: function () {
        if (/\/group\/active/.test(location.pathname)) {
          if (state.step1GroupCreated || new URLSearchParams(location.search).get('group_created') === '1') {
            return '#tableBody tr, .card-content, .page-header';
          }
          return 'a[href*="/group/create/"]';
        }
        if (/\/group\/create\/?$/.test(location.pathname)) {
          var fp = state.step1FormPhase || 0;
          if (fp === 1) return '#id_name';
          if (fp === 2) return '.radio-group';
          if (fp === 3) return '#id_description';
          if (fp === 4) return '.terms-card';
          if (fp === 5) return '#btnSubmit';
          return '.form-card.col-lg-8';
        }
        return 'a[href*="/group/active/"]';
      },
      resolveTitle: function () {
        if (/\/group\/active/.test(location.pathname)) {
          if (state.step1GroupCreated || new URLSearchParams(location.search).get('group_created') === '1') {
            return 'Turma Criada!';
          }
          return 'Cadastrar Turma';
        }
        if (/\/group\/create\/?$/.test(location.pathname)) {
          var fp = state.step1FormPhase || 0;
          if (fp === 1) return 'Nome da Turma';
          if (fp === 2) return 'Turno';
          if (fp === 3) return 'Descrição';
          if (fp === 4) return 'Termo de Aceite';
          if (fp === 5) return 'Cadastrar';
          return 'Criar uma Turma';
        }
        return 'Menu de Turmas';
      },
      resolveDesc: function () {
        if (/\/group\/active/.test(location.pathname)) {
          if (state.step1GroupCreated || new URLSearchParams(location.search).get('group_created') === '1') {
            return 'Turma criada! Clique em "Próximo" para criar uma atividade.';
          }
          return 'Aqui ficam todas as suas turmas. Clique em "Próximo" para criar a primeira.';
        }
        if (/\/group\/create\/?$/.test(location.pathname)) {
          var fp = state.step1FormPhase || 0;
          if (fp === 1) return 'Preenchemos o nome com "Tuor". Clique em "Próximo" para continuar.';
          if (fp === 2) return 'Selecionamos o turno "Integral". Clique em "Próximo" para continuar.';
          if (fp === 3) return 'Preenchemos a descrição. Clique em "Próximo" para continuar.';
          if (fp === 4) return 'Marque o termo de aceite para confirmar que as informações serão visíveis aos alunos. Clique em "Próximo".';
          if (fp === 5) return 'Tudo pronto! Clique em "Próximo" para cadastrar a turma.';
          return 'Vamos preencher o formulário juntos, campo por campo. Clique em "Próximo" para começar.';
        }
        return 'Aqui você acessa e gerencia suas turmas. Clique em "Próximo" para ir até lá.';
      },
      onNext: function () {
        var phase = state.step1Phase || 0;
        if (/\/group\/active/.test(location.pathname) &&
            (state.step1GroupCreated || new URLSearchParams(location.search).get('group_created') === '1')) {
          return false;
        }
        if (phase === 0) {
          state.step1Phase = 1;
          save();
          location.href = '/group/active/';
          return true;
        }
        if (phase === 1) {
          state.step1Phase = 2;
          state.step1FormPhase = 0;
          save();
          location.href = '/group/create/';
          return true;
        }
        if (/\/group\/create\/?$/.test(location.pathname)) {
          var fp = state.step1FormPhase || 0;
          if (fp === 0) {
            var nameEl = document.getElementById('id_name');
            if (nameEl) nameEl.value = 'Tuor';
            state.step1FormPhase = 1;
            save();
            activate();
            return true;
          }
          if (fp === 1) {
            var shiftEl = document.querySelector('input[name="shift"][value="Integral"]');
            if (shiftEl) shiftEl.click();
            state.step1FormPhase = 2;
            save();
            activate();
            return true;
          }
          if (fp === 2) {
            var descEl = document.getElementById('id_description');
            if (descEl) descEl.value = 'Tuor para conhecer o sistema';
            state.step1FormPhase = 3;
            save();
            activate();
            return true;
          }
          if (fp === 3) {
            var checkEl = document.getElementById('invalidCheck');
            if (checkEl) checkEl.checked = true;
            state.step1FormPhase = 4;
            save();
            activate();
            return true;
          }
          if (fp === 4) {
            state.step1FormPhase = 5;
            save();
            activate();
            return true;
          }
          if (fp === 5) {
            var submitEl = document.getElementById('btnSubmit');
            if (submitEl) submitEl.click();
            return true;
          }
        }
        return false;
      },
      onEnter: function () {
        if (/\/group\/active/.test(location.pathname) && new URLSearchParams(location.search).get('group_created') === '1') {
          state.step1GroupCreated = true;
          state.step1Phase = 0;
          state.step1FormPhase = 0;
          save();
          history.replaceState(null, '', location.pathname);
        }
      },
      navUrl: '/group/create/',
      navLabel: 'Ir para Criar Turma',
    },
    {
      n: 2,
      title: 'Criar uma Atividade',
      desc: 'Defina título, descrição e número de tentativas. Os exercícios são adicionados na próxima etapa.',
      match: function () {
        return /\/activity\/create\/?$/.test(location.pathname) ||
               /\/group\/active\/?$/.test(location.pathname);
      },
      selector: '.form-card',
      resolveSelector: function () {
        if (/\/activity\/create\/?$/.test(location.pathname)) {
          var fp = state.step2FormPhase || 0;
          if (fp === 1) return '#id_title';
          if (fp === 2) return '#id_description';
          if (fp === 3) return '#id_max_attempts';
          if (fp === 4) return 'label[for="id_manual_grading"]';
          if (fp === 5) return '#invalidCheck';
          if (fp === 6) return '.form-card form button[type="submit"]';
          return '.form-card';
        }
        return 'a[href*="/activity/list/"]';
      },
      resolveTitle: function () {
        if (/\/activity\/create\/?$/.test(location.pathname)) {
          var fp = state.step2FormPhase || 0;
          if (fp === 1) return 'Título';
          if (fp === 2) return 'Descrição';
          if (fp === 3) return 'Máximo de Tentativas';
          if (fp === 4) return 'Correção Manual';
          if (fp === 5) return 'Termo de Aceite';
          if (fp === 6) return 'Salvar e Continuar';
          return 'Criar uma Atividade';
        }
        return 'Criar uma Atividade';
      },
      resolveDesc: function () {
        if (/\/activity\/create\/?$/.test(location.pathname)) {
          var fp = state.step2FormPhase || 0;
          if (fp === 1) return 'Preenchemos o título com "Tuor Lista de Atividade". Clique em "Próximo" para continuar.';
          if (fp === 2) return 'Preenchemos a descrição. Clique em "Próximo" para continuar.';
          if (fp === 3) return 'Definimos o máximo de tentativas como 3. Clique em "Próximo" para continuar.';
          if (fp === 4) return 'A correção manual está desativada — o sistema corrigirá automaticamente. Clique em "Próximo".';
          if (fp === 5) return 'Marque o termo de aceite para confirmar que as informações serão visíveis aos alunos. Clique em "Próximo".';
          if (fp === 6) return 'Tudo pronto! Clique em "Próximo" para salvar a atividade e continuar.';
          return 'Vamos preencher o formulário juntos, campo por campo. Clique em "Próximo" para começar.';
        }
        return 'No menu acima, clique em "Atividades" para criar sua primeira atividade.';
      },
      onNext: function () {
        if (!/\/activity\/create\/?$/.test(location.pathname)) {
          state.step2FormPhase = 0;
          save();
          location.href = '/activity/create/';
          return true;
        }
        var fp = state.step2FormPhase || 0;
        if (fp === 0) {
          var titleEl = document.getElementById('id_title');
          if (titleEl) titleEl.value = 'Tuor Lista de Atividade';
          state.step2FormPhase = 1;
          save();
          activate();
          return true;
        }
        if (fp === 1) {
          var descEl = document.getElementById('id_description');
          if (descEl) descEl.value = 'Tuor para criar uma lista de atividade';
          state.step2FormPhase = 2;
          save();
          activate();
          return true;
        }
        if (fp === 2) {
          var attEl = document.getElementById('id_max_attempts');
          if (attEl) attEl.value = '3';
          state.step2FormPhase = 3;
          save();
          activate();
          return true;
        }
        if (fp === 3) {
          var mgEl = document.getElementById('id_manual_grading');
          if (mgEl) mgEl.checked = false;
          state.step2FormPhase = 4;
          save();
          activate();
          return true;
        }
        if (fp === 4) {
          var ckEl = document.getElementById('invalidCheck');
          if (ckEl) ckEl.checked = true;
          state.step2FormPhase = 5;
          save();
          activate();
          return true;
        }
        if (fp === 5) {
          state.step2FormPhase = 6;
          save();
          activate();
          return true;
        }
        if (fp === 6) {
          state.step2FormPhase = 0;
          state.step = 3;
          save();
          var submitEl = document.querySelector('.form-card form button[type="submit"]');
          if (submitEl) submitEl.click();
          return true;
        }
        return false;
      },
      navUrl: '/activity/create/',
      navLabel: 'Ir para Criar Atividade',
    },
    {
      n: 3,
      title: 'Adicionar Exercícios',
      desc: 'Clique em "+ Adicionar Exercício" para adicionar um exercício discursivo.',
      match: function () { return /\/activity\/update\/\d+\/?$/.test(location.pathname); },
      isReady: function () {
        var fp = state.step3Phase || 0;
        if (fp === 0) return !!document.querySelector('#add-exercise-slot');
        if (fp === 1) return !!document.querySelector('button[hx-get*="discursive"]');
        if (fp === 2) return !!document.getElementById('id_statement');
        return true;
      },
      selector: '#add-exercise-slot',
      resolveSelector: function () {
        var fp = state.step3Phase || 0;
        if (fp === 0) return '#add-exercise-slot button';
        if (fp === 1) return 'button[hx-get*="discursive"]';
        if (fp === 2) return '#add-exercise-slot';
        if (fp === 3) return '#id_statement';
        if (fp === 4) return '#id_points';
        if (fp === 5) return '#id_secondary-min_words';
        if (fp === 6) return '#id_secondary-max_words';
        if (fp === 7) return '#btnSubmit';
        return '#add-exercise-slot';
      },
      resolveTitle: function () {
        var fp = state.step3Phase || 0;
        if (fp === 0) return 'Adicionar Exercício';
        if (fp === 1) return 'Tipo: Discursiva';
        if (fp === 2) return 'Exercício Discursivo';
        if (fp === 3) return 'Enunciado';
        if (fp === 4) return 'Pontuação';
        if (fp === 5) return 'Mínimo de Palavras';
        if (fp === 6) return 'Máximo de Palavras';
        if (fp === 7) return 'Salvar Exercício';
        return 'Adicionar Exercícios';
      },
      resolveDesc: function () {
        var fp = state.step3Phase || 0;
        if (fp === 0) return 'Clique em "Próximo" para adicionar um exercício discursivo automaticamente.';
        if (fp === 1) return 'Selecionamos o tipo "Discursiva" — resposta em texto livre. Clique em "Próximo".';
        if (fp === 2) return 'Vamos preencher o exercício campo por campo. Clique em "Próximo" para começar.';
        if (fp === 3) return 'Preenchemos o enunciado. Clique em "Próximo" para continuar.';
        if (fp === 4) return 'Definimos a pontuação como 1. Clique em "Próximo" para continuar.';
        if (fp === 5) return 'O mínimo já está preenchido com 10 palavras (valor padrão). Clique em "Próximo".';
        if (fp === 6) return 'O máximo de palavras é opcional — pode deixar em branco. Clique em "Próximo".';
        if (fp === 7) return 'Tudo pronto! Clique em "Próximo" para salvar o exercício.';
        return 'Clique em "+ Adicionar Exercício" e escolha o tipo.';
      },
      onNext: function () {
        var fp = state.step3Phase || 0;
        if (fp === 0) {
          var addBtn = document.querySelector('#add-exercise-slot button');
          if (addBtn) addBtn.click();
          state.step3Phase = 1;
          save();
          activate();
          return true;
        }
        if (fp === 1) {
          var discBtn = document.querySelector('button[hx-get*="discursive"]');
          if (discBtn) discBtn.click();
          state.step3Phase = 2;
          save();
          activate();
          return true;
        }
        if (fp === 2) {
          var stEl = document.getElementById('id_statement');
          if (stEl) stEl.value = 'Tuor: Exercício discursivo de exemplo.';
          state.step3Phase = 3;
          save();
          activate();
          return true;
        }
        if (fp === 3) {
          var ptEl = document.getElementById('id_points');
          if (ptEl) ptEl.value = '1';
          state.step3Phase = 4;
          save();
          activate();
          return true;
        }
        if (fp === 4) {
          state.step3Phase = 5;
          save();
          activate();
          return true;
        }
        if (fp === 5) {
          state.step3Phase = 6;
          save();
          activate();
          return true;
        }
        if (fp === 6) {
          state.step3Phase = 7;
          save();
          activate();
          return true;
        }
        if (fp === 7) {
          state.step3Phase = 0;
          state.step = 4;
          save();
          activate();
          var subEl = document.getElementById('btnSubmit');
          if (subEl) subEl.click();
          return true;
        }
        return false;
      },
      navUrl: '/activity/list/',
      navLabel: 'Ir para Atividades',
    },
    {
      n: 4,
      title: 'Revisar a Atividade',
      desc: 'Com exercícios adicionados, clique em "Revisar" para ver como a atividade ficará para os alunos. Na tela de revisão, clique em "Finalizar" para vincular a uma turma.',
      waitingDesc: 'Adicione ao menos 1 exercício acima. Assim que o botão "Revisar" aparecer, o tour continuará automaticamente.',
      match: function () {
        return /\/activity\/update\/\d+\/?$/.test(location.pathname) ||
               /\/activity\/preview\/\d+\/?$/.test(location.pathname);
      },
      isReady: function () {
        if (/\/activity\/preview\/\d+\/?$/.test(location.pathname)) {
          var container = document.getElementById('finish-activity-action');
          return !!container && !container.classList.contains('d-none');
        }
        var el = document.getElementById('finish-actions-wrapper');
        return !!el && !el.classList.contains('d-none') && el.offsetParent !== null;
      },
      selector: '#finish-actions-wrapper',
      resolveSelector: function () {
        if (/\/activity\/preview\/\d+\/?$/.test(location.pathname)) {
          return '#finish-activity-action .btn-outline-primary';
        }
        return '#finish-actions-wrapper';
      },
      resolveTitle: function () {
        if (/\/activity\/preview\/\d+\/?$/.test(location.pathname)) {
          return 'Finalizar a Atividade';
        }
        return 'Revisar a Atividade';
      },
      resolveDesc: function () {
        if (/\/activity\/preview\/\d+\/?$/.test(location.pathname)) {
          return 'Confira os exercícios e clique em "Finalizar" para vincular a atividade a uma turma.';
        }
        return 'Com exercícios adicionados, clique em "Revisar" para ver como a atividade ficará para os alunos.';
      },
      onNext: function () {
        if (/\/activity\/update\/\d+\/?$/.test(location.pathname)) {
          var revisar = document.querySelector('#finish-actions-wrapper a.btn-outline-primary');
          if (revisar) {
            location.href = revisar.href;
          } else {
            var m = location.pathname.match(/\/activity\/update\/(\d+)/);
            if (m) location.href = '/activity/preview/' + m[1] + '/';
          }
          return true;
        }
        if (/\/activity\/preview\/\d+\/?$/.test(location.pathname)) {
          state.step = 5;
          save();
          var finBtn = document.querySelector('#finish-activity-action .btn-outline-primary');
          if (finBtn) finBtn.click();
          return true;
        }
        return false;
      },
      navUrl: '/activity/list/',
      navLabel: 'Ir para Atividades',
    },
    {
      n: 5,
      title: 'Vincular à Turma',
      desc: 'Clique em "Vincular" e selecione a turma.',
      match: function () {
        if (/\/activity\/list\/?$/.test(location.pathname)) return !state.step5Linked;
        return /\/activity\/assign\/\d+\/?$/.test(location.pathname);
      },
      isReady: function () {
        if (/\/activity\/assign\/\d+\/?$/.test(location.pathname)) {
          if (document.querySelector('#tableBody tr')) return true;
          var phase = state.step5Phase || 0;
          if (phase === 0) return true;
          var modal = document.getElementById('shareModal');
          var open = !!modal && modal.classList.contains('show');
          if (!open) return false;
          if (phase === 1) return !!document.getElementById('id_starts_at');
          if (phase === 2) return !!document.querySelector('.select2-container');
          if (phase === 3) return !!document.querySelector('.shared-users-list .shared-user-item');
          if (phase === 4) return true; /* submit button always present when modal is open */
          return true;
        }
        return true;
      },
      selector: '.btn[data-bs-target="#shareModal"]',
      resolveSelector: function () {
        if (/\/activity\/list\/?$/.test(location.pathname)) {
          return '#tableBody tr, .card-content, .page-header';
        }
        var phase = state.step5Phase || 0;
        if (phase === 5) return 'a[href*="/group/active/"]';
        if (document.querySelector('#tableBody tr')) return '#tableBody tr';
        if (phase === 0) return '[data-bs-target="#shareModal"]';
        if (phase === 1) return '.row.g-2.mb-3';
        if (phase === 2) return '.select2-container';
        if (phase === 3) return '.shared-users-list .shared-user-item';
        if (phase === 4) return '#shareModal .modal-footer button[type="submit"]';
        return '[data-bs-target="#shareModal"]';
      },
      resolveTitle: function () {
        if (/\/activity\/assign\/\d+\/?$/.test(location.pathname)) {
          var phase = state.step5Phase || 0;
          if (phase === 5) return 'Ir para Turmas';
          if (document.querySelector('#tableBody tr')) return 'Turma Vinculada!';
          if (phase === 1) return 'Definir Período';
          if (phase === 2) return 'Selecionar Turma';
          if (phase === 3) return 'Turma Selecionada';
          if (phase === 4) return 'Confirmar Vínculo';
        }
        return 'Vincular à Turma';
      },
      resolveDesc: function () {
        if (/\/activity\/list\/?$/.test(location.pathname)) {
          return 'Clique na atividade que criou para abrir e acesse a aba "Vincular a Turmas".';
        }
        var phase = state.step5Phase || 0;
        if (phase === 5) return 'Clique em "Turmas" no menu superior para acessar a turma e convidar os alunos.';
        if (document.querySelector('#tableBody tr')) {
          state.step5Linked = true;
          state.step5Phase = 0;
          save();
          return 'Turma vinculada! Clique em "Próximo" para continuar.';
        }
        if (phase === 0) return 'Clique em "Vincular" para abrir o formulário e configurar o vínculo com a turma.';
        if (phase === 1) return 'Configure o período de disponibilidade. As datas já foram preenchidas — ajuste se quiser e clique em "Próximo".';
        if (phase === 2) return 'Digitando "Tuor" no campo de busca e selecionando a turma criada no início do tour...';
        if (phase === 3) return 'Essa é a turma que você selecionou. Confira e clique em "Próximo".';
        if (phase === 4) return 'Tudo certo! Clique em "Vincular" para confirmar o vínculo.';
        return 'Clique em "Vincular" e selecione a turma.';
      },
      onNext: function () {
        if (!/\/activity\/assign\/\d+\/?$/.test(location.pathname)) return false;
        var phase = state.step5Phase || 0;
        /* Phase 5: navbar highlighted — auto-click "Turmas" and advance to step 6 */
        if (phase === 5) {
          state.step5Phase = 0;
          state.step = 6;
          save();
          var turmasLink = document.querySelector('a[href*="/group/active/"]');
          if (turmasLink) turmasLink.click(); else location.href = '/group/active/';
          return true;
        }
        /* "Turma Vinculada!" row visible — transition to navbar spotlight */
        if (document.querySelector('#tableBody tr')) {
          state.step5Phase = 5;
          save();
          activate();
          return true;
        }
        if (phase === 0) {
          var modalEl = document.getElementById('shareModal');
          if (modalEl && window.bootstrap) {
            var alreadyOpen = modalEl.classList.contains('show');
            if (!alreadyOpen) bootstrap.Modal.getOrCreateInstance(modalEl).show();
            /* Use timeout instead of shown.bs.modal to handle edge-cases where the
               event may not fire (modal already open, transition disabled, etc.) */
            setTimeout(function () {
              var now = new Date();
              var end = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
              var pad = function (n) { return (n < 10 ? '0' : '') + n; };
              var fmt = function (d) {
                return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
                       'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
              };
              var s = document.getElementById('id_starts_at');
              var e = document.getElementById('id_ends_at');
              if (s && !s.value) s.value = fmt(now);
              if (e && !e.value) e.value = fmt(end);
              state.step5Phase = 1;
              save();
              activate();
            }, alreadyOpen ? 50 : 450);
          }
          return true;
        }
        if (phase === 1) {
          state.step5Phase = 2;
          save();
          /* Watch for a group selection to auto-advance to phase 3 */
          var sharedList = document.querySelector('.shared-users-list');
          if (sharedList && !sharedList.__tourObs) {
            sharedList.__tourObs = new MutationObserver(function () {
              if (document.querySelector('.shared-users-list .shared-user-item')) {
                sharedList.__tourObs.disconnect();
                delete sharedList.__tourObs;
                state.step5Phase = 3;
                save();
                activate();
              }
            });
            sharedList.__tourObs.observe(sharedList, { childList: true });
          }
          activate();
          /* Auto-fill Select2 with the group "Tuor" via AJAX endpoint */
          setTimeout(function () {
            if (typeof $ === 'undefined' || !$('#id_groups').length) return;
            var $sel = $('#id_groups');
            var ajaxUrl = $sel.data('ajax--url');
            var fieldId = $sel.attr('data-field_id') || $sel.data('field_id');
            if (!ajaxUrl) return;
            /* Open dropdown for visual feedback while AJAX runs */
            $sel.select2('open');
            $.get(ajaxUrl, { term: 'Tuor', field_id: fieldId, page: 1 }, function (resp) {
              var item = resp && resp.results && resp.results[0];
              $sel.select2('close');
              if (!item) return;
              /* Append the option so Select2 knows about it, then fire the event
                 that share_modal.js listens to on $(document) */
              $sel.append(new Option(item.text, item.id, true, true));
              var evt = $.Event('select2:select');
              evt.params = { data: item };
              $(document).trigger(evt);
            });
          }, 50);
          return true;
        }
        if (phase === 2) {
          /* User clicked Próximo before selecting — wait in phase 3 for .shared-user-item */
          state.step5Phase = 3;
          save();
          activate();
          return true;
        }
        if (phase === 3) {
          /* Spotlight shared-user-item confirmed — move to submit button */
          state.step5Phase = 4;
          save();
          activate();
          return true;
        }
        if (phase === 4) {
          var submitBtn = document.querySelector('#shareModal .modal-footer button[type="submit"]');
          if (submitBtn) submitBtn.click();
          return true;
        }
        return false;
      },
      onEnter: function () {
        if (/\/activity\/assign\/\d+\/?$/.test(location.pathname)) {
          state.step5Url = location.pathname;
          save();
          /* Re-evaluate spotlight when modal closes so the table-row highlight appears
             immediately after "Vincular" is clicked (page reloads anyway, but this fires first) */
          var modalEl = document.getElementById('shareModal');
          if (modalEl && !modalEl.__tourHiddenObs) {
            modalEl.__tourHiddenObs = function () {
              setTimeout(activate, 100);
            };
            modalEl.addEventListener('hidden.bs.modal', modalEl.__tourHiddenObs);
          }
        }
      },
      autoAdvanceWhen: function () { return !!state.step5Linked; },
      navFn: function () {
        if (state.step5Linked) {
          state.step = 6;
          save();
          location.href = STEPS[5].navUrl;
          return;
        }
        location.href = state.step5Url || '/activity/list/';
      },
      navUrl: '/activity/list/',
      navLabel: 'Ir para Atividades',
    },
    {
      n: 6,
      title: 'Convidar Alunos',
      desc: 'Na aba Compartilhamento → Alunos, clique em "Convidar Aluno" e gere um link temporário. Os alunos se matriculam ao acessar.',
      match: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) return /\/group\/active\/?$/.test(location.pathname);
        if (phase === 1) return /\/group\/\d+\/?$/.test(location.pathname) && !/share/.test(location.pathname);
        if (phase === 2) return /\/group\/\d+\/share\/?$/.test(location.pathname) && !location.search.includes('students');
        /* phase 3 */
        return /\/group\/\d+\/share\/?$/.test(location.pathname) && location.search.includes('students');
      },
      isReady: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) return true; /* server-rendered; card always present */
        if (phase === 1) return !!document.querySelector('a.nav-link[href*="/share/"]');
        if (phase === 2) return !!document.querySelector('a[href*="share_view=students"]');
        if (phase === 3) return true; /* Convidar Aluno button always present */
        if (phase === 4) return !!document.querySelector('#shareModal.show #group-invite-action:not(.d-none) button');
        if (phase === 5) return !!document.querySelector('#latestInviteUrl');
        return !!document.querySelector('#copyInviteUrl');
      },
      resolveSelector: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) return '#tableBody tr, .card-content, .page-header';
        if (phase === 1) return 'a.nav-link[href*="/share/"]';
        if (phase === 2) return 'a[href*="share_view=students"]';
        if (phase === 3) return '[data-bs-target="#shareModal"]';
        if (phase === 4) return '#group-invite-action button';
        if (phase === 5) return '#latestInviteUrl';
        return '#copyInviteUrl';
      },
      resolveTitle: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) return 'Sua Turma';
        if (phase === 1) return 'Compartilhamento';
        if (phase === 2) return 'Área de Alunos';
        if (phase === 3) return 'Convidar Alunos';
        if (phase === 4) return 'Gerar Link';
        if (phase === 5) return 'Link de Convite';
        return 'Copiar Link';
      },
      resolveDesc: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) return 'Essa é a turma "Tuor" que você criou. Clique em "Próximo" para abrí-la.';
        if (phase === 1) return 'Clique em "Próximo" para acessar a aba de Compartilhamento e convidar alunos.';
        if (phase === 2) return 'Clique em "Próximo" para acessar a aba de Alunos.';
        if (phase === 3) return 'Clique em "Próximo" para abrir o painel de convite e gerar um link para seus alunos.';
        if (phase === 4) return 'Clique em "Próximo" para gerar um link temporário de convite.';
        if (phase === 5) return 'Este é o link de convite! Compartilhe com seus alunos para que eles se matriculem na turma.';
        return 'Clique em "Próximo" para copiar o link. O tour será concluído em seguida.';
      },
      onNext: function () {
        var phase = state.step6Phase || 0;
        if (phase === 0) {
          state.step6Phase = 1;
          save();
          var row = document.querySelector('#tableBody tr.clickable-row');
          if (row && row.dataset.href) {
            location.href = row.dataset.href;
          } else {
            var cardLink = document.querySelector('.card-content a[href*="/group/"]');
            if (cardLink) location.href = cardLink.href; else location.href = '/group/active/';
          }
          return true;
        }
        if (phase === 1) {
          state.step6Phase = 2;
          save();
          var shareLink = document.querySelector('a.nav-link[href*="/share/"]');
          if (shareLink) shareLink.click();
          return true;
        }
        if (phase === 2) {
          state.step6Phase = 3;
          save();
          var alunosLink = document.querySelector('a[href*="share_view=students"]');
          if (alunosLink) alunosLink.click();
          return true;
        }
        if (phase === 3) {
          state.step6Phase = 4;
          save();
          var inviteBtn = document.querySelector('[data-bs-target="#shareModal"]');
          if (inviteBtn) inviteBtn.click();
          activate(); /* isReady(4) waits for modal .show via watchForReady */
          return true;
        }
        if (phase === 4) {
          state.step6Phase = 5;
          save();
          var gerarBtn = document.querySelector('#group-invite-action button');
          if (gerarBtn) gerarBtn.click();
          activate(); /* isReady(5) waits for #latestInviteUrl via watchForReady */
          return true;
        }
        if (phase === 5) {
          state.step6Phase = 6;
          save();
          activate();
          return true;
        }
        /* phase 6: copy link, close modal, go to teachers share view (step 7) */
        var copyBtn = document.querySelector('#copyInviteUrl');
        if (copyBtn) copyBtn.click();
        var modalEl = document.getElementById('shareModal');
        if (modalEl && typeof bootstrap !== 'undefined') {
          var bsModal = bootstrap.Modal.getInstance(modalEl);
          if (bsModal) bsModal.hide();
        }
        state.step6Phase = 0;
        state.step = 7;
        save();
        var m6 = location.pathname.match(/\/group\/(\d+)\//);
        location.href = m6 ? '/group/' + m6[1] + '/share/?share_view=teachers' : '/group/active/';
        return true;
      },
      navUrl: '/group/active/',
      navLabel: 'Ir para Turmas',
    },
    {
      n: 7,
      title: 'Compartilhar com Professor',
      desc: 'Na aba Compartilhamento → Professores, busque pelo nome do colega e compartilhe a turma.',
      match: function () {
        return /\/group\/\d+\/share\/?$/.test(location.pathname) && location.search.includes('teachers');
      },
      isReady: function () {
        var phase = state.step7Phase || 0;
        if (phase === 0) return !!document.querySelector('[data-bs-target="#shareModal"]');
        /* phase 1: wait for modal to open */
        return !!document.querySelector('#shareModal.show');
      },
      resolveSelector: function () {
        var phase = state.step7Phase || 0;
        if (phase === 0) return '[data-bs-target="#shareModal"]';
        return '#shareModal .modal-body, #shareModal';
      },
      resolveTitle: function () {
        return (state.step7Phase || 0) === 0 ? 'Compartilhar com Professor' : 'Compartilhamento';
      },
      resolveDesc: function () {
        if ((state.step7Phase || 0) === 0) {
          return 'Aqui você compartilha a turma com outros professores. Clique em "Próximo" para ver o painel.';
        }
        return 'Neste painel você buscaria o professor pelo nome e clicaria em "Compartilhar". Clique em "Próximo" para avançar para a Revisão.';
      },
      onNext: function () {
        var phase = state.step7Phase || 0;
        if (phase === 0) {
          state.step7Phase = 1;
          save();
          var btn = document.querySelector('[data-bs-target="#shareModal"]');
          if (btn) btn.click();
          activate(); /* watchForReady aguarda #shareModal.show */
          return true;
        }
        /* phase 1: fechar modal e navegar para revisão (step 8) */
        state.step7Phase = 0;
        state.step = 8;
        save();
        var modalEl = document.getElementById('shareModal');
        if (modalEl && typeof bootstrap !== 'undefined') {
          var bsModal = bootstrap.Modal.getInstance(modalEl);
          if (bsModal) bsModal.hide();
        }
        var m7 = location.pathname.match(/\/group\/(\d+)\//);
        location.href = m7 ? '/group/' + m7[1] + '/' : '/group/active/';
        return true;
      },
      navUrl: '/group/active/',
      navLabel: 'Ir para Professores',
      navFn: function () {
        var m = location.pathname.match(/\/group\/(\d+)\/share/);
        if (m) { location.href = '/group/' + m[1] + '/share/?share_view=teachers'; return; }
        location.href = '/group/active/';
      },
    },
    {
      n: 8,
      title: 'Acompanhar Revisão',
      desc: 'Na página da turma (aba Revisão), veja as atividades com contagem de submissões pendentes. Clique em Corrigir para iniciar a avaliação.',
      match: function () {
        /* GroupReviewView serve tanto /group/:id/ quanto /group/:id/review/ */
        return /^\/group\/\d+\/$/.test(location.pathname) ||
               /^\/group\/\d+\/review\/$/.test(location.pathname);
      },
      isReady: function () {
        var phase = state.step8Phase || 0;
        if (phase === 0) return !!document.querySelector('a.nav-link.active');
        return true;
      },
      resolveSelector: function () {
        var phase = state.step8Phase || 0;
        if (phase === 0) return 'a.nav-link.active';
        if (phase === 1) return '.col-lg-8 .detail-left-card';
        return '.review-row a.btn';
      },
      resolveTitle: function () {
        var phase = state.step8Phase || 0;
        if (phase === 0) return 'Aba Revisão';
        if (phase === 1) return 'Acompanhar Revisão';
        return 'Corrigir Submissões';
      },
      resolveDesc: function () {
        var phase = state.step8Phase || 0;
        if (phase === 0) return 'Esta é a aba Revisão — aqui aparecem as atividades com submissões pendentes dos alunos. Clique em "Próximo" para continuar.';
        if (phase === 1) return 'Aqui você acompanha as atividades com submissões pendentes. Clique em "Próximo" para ver o botão de correção.';
        return 'Clique em "Próximo" para abrir a lista de submissões e iniciar a avaliação exercício a exercício.';
      },
      onNext: function () {
        var phase = state.step8Phase || 0;
        if (phase === 0) {
          /* tab já está ativo na URL atual — só avança a fase, sem navegar */
          state.step8Phase = 1;
          save();
          activate();
          return true;
        }
        if (phase === 1) {
          state.step8Phase = 2;
          save();
          activate();
          return true;
        }
        /* phase 2: click Corrigir and go to step 9 */
        state.step8Phase = 0;
        var corrigirBtn = document.querySelector('.review-row a.btn');
        if (corrigirBtn) {
          state.step = 9;
          save();
          corrigirBtn.click();
          return true;
        }
        save();
        return false;
      },
      navUrl: '/group/active/',
      navLabel: 'Ir para Turmas',
    },
    {
      n: 9,
      title: 'Corrigir Submissões',
      desc: 'Veja os alunos organizados em três colunas: Para Correção, Concluíram e Pendentes. Clique em Corrigir para avaliar exercício a exercício.',
      match: function () { return /\/student\/activity\/\d+\/submissions\/?$/.test(location.pathname); },
      selector: '.row.g-3.align-items-start',
      navUrl: '/group/active/',
      navLabel: 'Ir para Turmas',
    },
  ];

  /* ── Persistence ──────────────────────────────────────────────── */
  var KEY = 'educatrix_tour_v2_u' + (window.__tourUserId__ || '0');

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  var state = load();
  if (typeof state.step   !== 'number')  state.step   = 1;
  if (!Array.isArray(state.done))        state.done   = [];
  if (typeof state.active !== 'boolean') state.active = false;

  /* ── DOM elements ─────────────────────────────────────────────── */
  var overlay       = null;
  var highlight     = null;
  var tooltip       = null;
  var navBar        = null;
  var fab           = null;
  var readyObserver = null;

  function buildDOM() {
    /* Overlay */
    overlay = document.createElement('div');
    overlay.id = 'tour-overlay';
    overlay.style.display = 'none';
    document.body.appendChild(overlay);

    /* Highlight box */
    highlight = document.createElement('div');
    highlight.id = 'tour-highlight';
    highlight.style.display = 'none';
    document.body.appendChild(highlight);

    /* Tooltip */
    tooltip = document.createElement('div');
    tooltip.id = 'tour-tooltip';
    tooltip.style.display = 'none';
    tooltip.innerHTML =
      '<div class="tour-tt-eyebrow">' +
        '<span>Tour guiado</span>' +
        '<span class="tour-tt-counter" id="tourCounter"></span>' +
      '</div>' +
      '<div class="tour-tt-dots" id="tourDots"></div>' +
      '<div class="tour-tt-title" id="tourTitle"></div>' +
      '<div class="tour-tt-desc" id="tourDesc"></div>' +
      '<div class="tour-tt-actions">' +
        '<button class="btn btn-sm btn-outline-secondary rounded-5 px-3" id="tourPrev">← Anterior</button>' +
        '<button class="btn btn-sm btn-primary rounded-5 px-3" id="tourNext">Próximo →</button>' +
      '</div>';
    document.body.appendChild(tooltip);

    /* Navigation bar (wrong page) */
    navBar = document.createElement('div');
    navBar.id = 'tour-nav-bar';
    navBar.className = 'tour-bar--hidden';
    navBar.innerHTML =
      '<span style="opacity:.6;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em">Tour</span>' +
      '<span id="navBarStep" style="font-weight:700"></span>' +
      '<span id="navBarTitle" style="opacity:.85"></span>' +
      '<button class="btn btn-sm btn-warning rounded-5 px-3" id="navBarBtn" style="font-size:.8rem"></button>' +
      '<button class="btn btn-sm btn-link text-white-50 ps-1 pe-0" id="navBarClose" style="font-size:.9rem;text-decoration:none">✕</button>';
    document.body.appendChild(navBar);

    /* FAB (always visible when active, pulsing on right page) */
    fab = document.createElement('button');
    fab.id = 'tour-fab';
    fab.className = 'tour-fab--hidden';
    fab.innerHTML =
      '<span class="tour-fab-icon"><i class="bi bi-map"></i></span>' +
      '<span class="tour-fab-right">' +
        '<span id="fabLabel">Tour</span>' +
        '<span class="tour-fab-sub" id="fabSub"></span>' +
      '</span>';
    document.body.appendChild(fab);

    /* Wire events */
    document.getElementById('tourPrev').addEventListener('click', prevStep);
    document.getElementById('tourNext').addEventListener('click', nextStep);

    document.getElementById('navBarClose').addEventListener('click', endTour);
    document.getElementById('navBarBtn').addEventListener('click', navigateToStep);
    fab.addEventListener('click', onFabClick);
  }

  /* ── Step helpers ─────────────────────────────────────────────── */
  function currentStep() {
    return STEPS.find(function (s) { return s.n === state.step; }) || STEPS[0];
  }

  function findEl(selector) {
    var parts = selector.split(',');
    for (var i = 0; i < parts.length; i++) {
      try {
        var el = document.querySelector(parts[i].trim());
        if (el) return el;
      } catch (e) {}
    }
    return null;
  }

  function markDone(n) {
    if (state.done.indexOf(n) === -1) state.done.push(n);
  }

  /* ── Ready observer ──────────────────────────────────────────── */
  function watchForReady(step) {
    if (readyObserver) { readyObserver.disconnect(); readyObserver = null; }
    if (!step.isReady) return;
    readyObserver = new MutationObserver(function () {
      if (state.active && currentStep().n === step.n && step.isReady()) {
        readyObserver.disconnect();
        readyObserver = null;
        activate();
      }
    });
    readyObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ['class'],
      childList: true,
      subtree: true,
    });
  }

  /* ── Spotlight ────────────────────────────────────────────────── */
  function showSpotlight(el) {
    var pad = 8;
    var rect = el.getBoundingClientRect();
    overlay.style.display = 'block';
    highlight.style.display = 'block';
    highlight.style.top    = (rect.top    - pad) + 'px';
    highlight.style.left   = (rect.left   - pad) + 'px';
    highlight.style.width  = (rect.width  + pad * 2) + 'px';
    highlight.style.height = (rect.height + pad * 2) + 'px';
  }

  function hideSpotlight() {
    if (overlay) { overlay.style.display = 'none'; overlay.style.clipPath = ''; }
    if (highlight) highlight.style.display = 'none';
    if (tooltip)   tooltip.style.display   = 'none';
  }

  /* ── Tooltip positioning ──────────────────────────────────────── */
  function positionTooltip(el) {
    var TW = 320, TH = 220;
    var pad = 8;
    var r = el.getBoundingClientRect();
    var vW = window.innerWidth, vH = window.innerHeight;
    var top, left;

    tooltip.className = '';  /* reset arrow class */

    /* Try bottom */
    if (r.bottom + 20 + TH < vH) {
      top  = r.bottom + 16;
      left = Math.min(r.left, vW - TW - 12);
      left = Math.max(12, left);
      tooltip.classList.add('arrow-top');
    }
    /* Try top */
    else if (r.top - 20 - TH > 0) {
      top  = r.top - TH - 16;
      left = Math.min(r.left, vW - TW - 12);
      left = Math.max(12, left);
      tooltip.classList.add('arrow-bottom');
    }
    /* Try right */
    else if (r.right + 16 + TW < vW) {
      top  = Math.max(12, Math.min(r.top, vH - TH - 12));
      left = r.right + 16;
      tooltip.classList.add('arrow-left');
    }
    /* Try left */
    else {
      top  = Math.max(12, Math.min(r.top, vH - TH - 12));
      left = r.left - TW - 16;
      left = Math.max(12, left);
      tooltip.classList.add('arrow-right');
    }

    tooltip.style.top       = top  + 'px';
    tooltip.style.left      = left + 'px';
    tooltip.style.transform = '';
    tooltip.style.display   = 'block';
  }

  function renderTooltip() {
    var step = currentStep();
    var n = state.step;

    /* Dots */
    var dotsEl = document.getElementById('tourDots');
    dotsEl.innerHTML = '';
    STEPS.forEach(function (s) {
      var d = document.createElement('span');
      d.className = 'tour-tt-dot' +
        (s.n === n ? ' active' : state.done.indexOf(s.n) !== -1 ? ' done' : '');
      dotsEl.appendChild(d);
    });

    document.getElementById('tourCounter').textContent = n + ' / ' + STEPS.length;
    document.getElementById('tourTitle').textContent   = step.title;
    document.getElementById('tourDesc').textContent    = step.desc;
    document.getElementById('tourPrev').disabled       = n === 1;
    document.getElementById('tourNext').disabled       = false;
    document.getElementById('tourNext').textContent    =
      n === STEPS.length ? 'Concluir ✓' : 'Próximo →';
  }

  /* ── FAB rendering ────────────────────────────────────────────── */
  function renderFab(onPage) {
    var step = currentStep();
    fab.className = state.active ? '' : 'tour-fab--hidden';
    document.getElementById('fabLabel').textContent =
      onPage ? ('✓ Passo ' + state.step + '/' + STEPS.length) : ('Passo ' + state.step + '/' + STEPS.length);
    document.getElementById('fabSub').textContent =
      onPage ? step.title : step.navLabel;
    fab.style.background = onPage ? '#1d4ed8' : '#1e293b';
  }

  /* ── Nav bar (wrong page) ─────────────────────────────────────── */
  function showNavBar() {
    var step = currentStep();
    document.getElementById('navBarStep').textContent  = 'Passo ' + state.step;
    document.getElementById('navBarTitle').textContent = step.title;
    document.getElementById('navBarBtn').textContent   = step.navLabel + ' →';
    navBar.classList.remove('tour-bar--hidden');
  }

  function hideNavBar() {
    navBar.classList.add('tour-bar--hidden');
  }

  /* ── Main activate ────────────────────────────────────────────── */
  function activate() {
    if (!state.active) {
      hideSpotlight();
      hideNavBar();
      fab.className = 'tour-fab--hidden';
      return;
    }

    var step = currentStep();
    var onPage = step.match();

    markDone(state.step);
    save();

    if (onPage) {
      hideNavBar();

      /* Notify step it's being activated on its page */
      if (step.onEnter) { step.onEnter(); }

      /* Step has a readiness condition and it's not met yet — wait silently */
      if (step.isReady && !step.isReady()) {
        hideSpotlight();
        renderFab(true);
        watchForReady(step);
        return;
      }

      /* Element ready — clear any pending observer */
      if (readyObserver) { readyObserver.disconnect(); readyObserver = null; }

      var selectorStr = step.resolveSelector ? step.resolveSelector() : step.selector;
      var el = step.resolveEl ? step.resolveEl() : findEl(selectorStr);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        renderFab(true);
        renderTooltip();
        if (step.resolveTitle) {
          document.getElementById('tourTitle').textContent = step.resolveTitle();
        }
        if (step.resolveDesc) {
          document.getElementById('tourDesc').textContent = step.resolveDesc();
        }
        setTimeout(function () {
          showSpotlight(el);
          positionTooltip(el);
        }, 450);
      } else {
        /* Element not found on this page — just show tooltip centered */
        hideSpotlight();
        renderFab(true);
        renderTooltip();
        if (step.resolveTitle) {
          document.getElementById('tourTitle').textContent = step.resolveTitle();
        }
        if (step.resolveDesc) {
          document.getElementById('tourDesc').textContent = step.resolveDesc();
        }
        tooltip.style.display   = 'block';
        tooltip.style.top       = '50%';
        tooltip.style.left      = '50%';
        tooltip.style.transform = 'translate(-50%, -50%)';
        tooltip.className       = '';
      }
    } else {
      /* Step reports it's already completed — skip forward automatically */
      if (step.autoAdvanceWhen && step.autoAdvanceWhen()) {
        hideSpotlight();
        state.step++;
        save();
        activate();
        return;
      }
      hideSpotlight();
      renderFab(false);
      showNavBar();
    }
  }

  /* ── Navigation ───────────────────────────────────────────────── */
  function nextStep() {
    var step = currentStep();
    if (state.step >= STEPS.length) {
      endTour(true);
      return;
    }
    /* Allow step to intercept navigation (e.g. switch sub-tab) */
    if (step.onNext && step.onNext()) return;
    hideSpotlight();
    state.step++;
    save();
    activate();
  }

  function prevStep() {
    if (state.step <= 1) return;
    hideSpotlight();
    state.step--;
    save();
    activate();
  }

  function navigateToStep() {
    var step = currentStep();
    if (step.navFn) { step.navFn(); return; }
    location.href = step.navUrl;
  }

  function onFabClick() {
    var step = currentStep();
    if (step.match()) {
      /* Re-show spotlight if dismissed */
      activate();
    } else {
      navigateToStep();
    }
  }

  function endTour(completed) {
    hideSpotlight();
    hideNavBar();
    if (readyObserver) { readyObserver.disconnect(); readyObserver = null; }
    fab.className = 'tour-fab--hidden';
    if (completed) {
      state.active = false;
      save();
      if (typeof showNotificationPopup === 'function') {
        showNotificationPopup('Success', 'Tour concluído! Você já conhece o ciclo completo do Educatrix.');
      }
    } else {
      try { localStorage.removeItem(KEY); } catch (e) {}
      state = { step: 1, done: [], active: false };
    }
  }

  /* ── Reposition on resize/scroll ─────────────────────────────── */
  window.addEventListener('resize', function () {
    if (!state.active) return;
    var step = currentStep();
    if (!step.match()) return;
    var el = findEl(step.selector);
    if (el) { showSpotlight(el); positionTooltip(el); }
  });

  /* ── Public API ───────────────────────────────────────────────── */
  window.tourStart = function () {
    state.active            = true;
    state.step              = 1;
    state.done              = [];
    state.step1Phase        = 0;
    state.step1FormPhase    = 0;
    state.step1GroupCreated = false;
    state.step2FormPhase    = 0;
    state.step3Phase        = 0;
    state.step5Phase        = 0;
    state.step5Linked       = false;
    state.step6Phase        = 0;
    state.step7Phase        = 0;
    state.step8Phase        = 0;
    save();
    if (!STEPS[0].match()) {
      location.href = STEPS[0].navUrl;
    } else {
      activate();
    }
  };

  window.tourResume = function () {
    state.active = true;
    save();
    var step = currentStep();
    if (!step.match()) {
      if (step.navFn) { step.navFn(); return; }
      location.href = step.navUrl;
    } else {
      activate();
    }
  };

  window.tourReset = function () {
    state = { step: 1, done: [], active: false };
    save();
    hideSpotlight();
    hideNavBar();
    fab.className = 'tour-fab--hidden';
  };

  window.tourState = function () { return state; };

  /* ── Bootstrap ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    buildDOM();
    /* If arriving from group creation, force step 1 regardless of prior state */
    if (state.active && new URLSearchParams(location.search).get('group_created') === '1') {
      state.step = 1;
      state.step1GroupCreated = false;
      save();
    }
    activate();
  });

})();
