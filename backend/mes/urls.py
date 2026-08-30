from django.urls import path

from . import views

urlpatterns = [
    # F1–F5 writes
    path('dryer/cycles/', views.dryer_cycle_create, name='dryer-cycle-create'),
    path('setting/events/', views.setting_event_create, name='setting-event-create'),
    path('kiln/pushes/', views.kiln_push_create, name='kiln-push-create'),
    path('packing/headers/', views.packing_header_create, name='packing-header-create'),
    # F7 read
    path('dashboard/wagon-journey/', views.wagon_journey, name='wagon-journey'),
    # Dimension dropdowns
    path('dimensions/operators/', views.operator_list, name='operator-list'),
    path('dimensions/products/', views.product_list, name='product-list'),
    path('dimensions/glazes/', views.glaze_list, name='glaze-list'),
    path('dimensions/wagons/', views.wagon_list, name='wagon-list'),
    path('dimensions/chambers/', views.chamber_list, name='chamber-list'),
    path('dimensions/sensors/', views.sensor_list, name='sensor-list'),
    path('dashboard/awaiting-discharge/', views.awaiting_discharge_list, name='awaiting-discharge-list'),
]
