BASE_INTERFACE = {
    'admin': True,
    'profile': True,
    'main': True,
    'orders': True,
    'oligomaps': True,
    'materials': True,
    'equipment': True,
    'lcms': True,
    'statistic': True,
    'order_list_tab': True,
    'new_order_tab': True,
    'order_content_tab': True,
    'delete_stock_transactions': False,
    'inner_client': False,
    'client_id': None,
    'measurements_stats': False,
}

ADMIN_INTERFACE = BASE_INTERFACE.copy()
ADMIN_INTERFACE.update({
    'lcms': True,
    'admin': True,
})

LAB_INTERFACE = BASE_INTERFACE.copy()
LAB_INTERFACE['admin'] = False

SYNTH_INTERFACE = BASE_INTERFACE.copy()
SYNTH_INTERFACE['admin'] = False

PROD_INTERFACE = BASE_INTERFACE.copy()
PROD_INTERFACE['admin'] = False


AVAILABLE_PERMISSIONS = {
    'lab_manager': LAB_INTERFACE,
    'synth_manager': SYNTH_INTERFACE,
    'prod_manager': PROD_INTERFACE,
    'admin': ADMIN_INTERFACE
}