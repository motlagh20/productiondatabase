from django.urls import path

from . import views

urlpatterns = [
    # F1–F5 writes
    path('dryer/cycles/', views.dryer_cycle_create, name='dryer-cycle-create'),
    path('dryer/readings/', views.dryer_reading_create, name='dryer-reading-create'),
    path('dryer/unload/', views.dryer_unload, name='dryer-unload'),
    path('setting/events/', views.setting_event_create, name='setting-event-create'),
    path('kiln/pushes/', views.kiln_push_create, name='kiln-push-create'),
    path('packing/headers/', views.packing_header_create, name='packing-header-create'),
    # F7 read
    path('dashboard/wagon-journey/', views.wagon_journey, name='wagon-journey'),
    # New GET list endpoints (UI merge)
    path('dryer/chambers/status/', views.dryer_chamber_status, name='dryer-chamber-status'),
    path('dryer/cycles/list/', views.dryer_cycle_list, name='dryer-cycle-list'),
    path('setting/events/list/', views.setting_event_list, name='setting-event-list'),
    path('kiln/pushes/list/', views.kiln_push_list, name='kiln-push-list'),
    # Dimension dropdowns
    path('dimensions/operators/', views.operator_list, name='operator-list'),
    path('dimensions/products/', views.product_list, name='product-list'),
    path('dimensions/glazes/', views.glaze_list, name='glaze-list'),
    path('dimensions/wagons/', views.wagon_list, name='wagon-list'),
    path('dimensions/chambers/', views.chamber_list, name='chamber-list'),
    path('dimensions/sensors/', views.sensor_list, name='sensor-list'),
    path('dashboard/awaiting-discharge/', views.awaiting_discharge_list, name='awaiting-discharge-list'),
    path('dashboard/active-wagons/', views.active_wagons_list, name='active-wagons-list'),
]
