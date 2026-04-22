from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from main_app import views
from main_app.views import check_username
from django.conf import settings             # <-- ADD THIS
from django.conf.urls.static import static

urlpatterns = [
    # --- ADMIN ---
    path('admin/', admin.site.urls),
    path('my-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('update-settings/', views.update_settings, name='update_settings'),
    path('update_admin_profile/', views.update_admin_profile, name='update_admin_profile'),
    path('update_admin_password/', views.update_admin_password, name='update_admin_password'),
    path('update-site-settings/', views.update_site_settings, name='update_site_settings'),
    path('delete_customer/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    path('delete-ph-request/<int:req_id>/', views.delete_ph_request, name='delete_ph_request'),
    path('apply-discount/', views.apply_discount, name='apply_discount'),
    # --- HOME & AUTH ---
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='main_app/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login-success/', views.login_success, name='login_success'),
    path('crop-prediction/', views.crop_prediction, name='crop_prediction'),

    # --- REGISTRATION ---
    path('register/', views.register, name='register'),
    path('register/farmer/', views.register_farmer, name='register_farmer'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),

    # --- FARMER DASHBOARD ---
    path('farmer-dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('add-crop/', views.add_crop, name='add_crop'),
    path('edit-crop/<int:crop_id>/', views.edit_crop, name='edit_crop'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('dashboard/order/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('send-suggestion/', views.send_suggestion, name='send_suggestion'),
    path('shop/message/<int:farmer_id>/', views.send_farmer_message, name='send_farmer_message'),
    path('dashboard/messages/delete/', views.delete_messages, name='delete_messages'),
    path('delete-crop/<int:crop_id>/', views.delete_crop, name='delete_crop'),
    path('dashboard/task/add/', views.add_farm_task, name='add_farm_task'),
    path('dashboard/settings/update/', views.update_farmer_settings, name='update_farmer_settings'),
    path('dashboard/settings/password/', views.change_password, name='change_password'),
    path('order/return-request/<int:order_id>/', views.request_return, name='request_return'),
    path('request-return/<int:order_id>/', views.request_return, name='request_return'),

    # --- SHOPPING ---
    path('shop/<int:farmer_id>/', views.farmer_shop, name='farmer_shop'),

    # --- CART & CHECKOUT ---
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:crop_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:crop_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('cart/process/', views.process_cart, name='process_cart'),

    # Single Item Checkout
    path('checkout/<int:crop_id>/', views.checkout, name='checkout'),
    path('confirm-payment/<int:crop_id>/', views.confirm_payment, name='confirm_payment'),

    # --- ORDERS ---
    path('my-orders/', views.my_orders, name='my_orders'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path('bill/<int:order_id>/', views.download_bill, name='download_bill'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),

    # --- ADMIN ACTIONS ---
    path('my-admin/approve/<int:id>/', views.approve_farmer, name='approve_farmer'),
    path('my-admin/reject/<int:id>/', views.reject_farmer, name='reject_farmer'),
    path('delete-farmer/<int:farmer_id>/', views.delete_farmer, name='delete_farmer'),
    path('update-farmer-status/<int:farmer_id>/', views.update_farmer_details, name='update_farmer_details'),
    path('delete-suggestion/<int:id>/', views.delete_suggestion, name='delete_suggestion'),
    path('admin-dashboard/delete-crop/<int:crop_id>/', views.admin_delete_crop, name='admin_delete_crop'),
    path('admin-dashboard/grant-subsidy/<int:farmer_id>/', views.grant_subsidy, name='grant_subsidy'),

    # --- CUSTOMER ACTIONS ---
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    # FIX: Added missing update_profile path to prevent 500 server crashes in templates!
    path('update-profile/', views.edit_profile, name='update_profile'),

    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='main_app/password_change.html'),
         name='password_change'),
    path('password-change/done/',
         auth_views.PasswordChangeDoneView.as_view(template_name='main_app/password_change_done.html'),
         name='password_change_done'),
    path('send-chat-message/', views.send_chat_message, name='send_chat_message'),
    path('my-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('update-address/', views.update_address, name='update_address'),
    path('process-return/<int:order_id>/<str:action>/', views.process_return, name='process_return'),

    path('submit-ph-request/', views.submit_ph_request, name='submit_ph_request'),
    path('update-ph-level/<int:req_id>/', views.update_ph_level, name='update_ph_level'),
    path('check-username/', check_username, name='check_username'),
]

# === STANDARD DJANGO CONFIG FOR SERVING MEDIA (IMAGES/VIDEOS) ===
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)