def get_btn_action(action: list, app_name: str):
    
    if not isinstance(action, list):
        raise ValueError("O parâmetro 'action' deve ser uma lista.")

    actions = {
        'archive': {
            'url': f'{app_name}:archive',
            'method': 'post',
            'icon': 'bi-inbox',
            'class': 'btn-outline-success',
        },
        'delete': {
            'url': f'{app_name}:delete',
            'method': 'get',
            'icon': 'bi-trash',
            'class': 'btn-outline-danger',
        },
         'unshare': {
            'url': f'{app_name}:unshare',
            'method': 'post',
            'icon': 'bi-trash',
            'class': 'btn-outline-danger',
        },
        'update': {
            'url': f'{app_name}:update',
            'method': 'get',
            'icon': 'bi-pencil',
            'class': 'btn-outline-primary',
        },
        'assign_update': {
            'url': f'{app_name}:assign_update',
            'method': 'get',
            'icon': 'bi-pencil',
            'class': 'btn-outline-primary',
        },
    }

    return [actions.get(act) for act in action]
