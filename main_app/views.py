import json
import calendar
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.db.models.functions import TruncMonth
from django.core.exceptions import ObjectDoesNotExist
from .models import SiteSetting
from django.urls import reverse
from .models import (
    User, FarmerProfile, CustomerProfile, Crop, Order, CartItem,
    Suggestion, FarmerMessage, ActivityLog, DailyStats, ChatMessage,
    SiteSettings, Payout, Dispute, PHTestRequest, AdminProfile
)
from .forms import (
    UserForm, FarmerProfileForm, CustomerProfileForm, CropForm,
    UserUpdateForm, FarmerProfileUpdateForm, CustomerProfileUpdateForm
)

# --- 1. AUTHENTICATION & HOME ---
def home(request):
    query = request.GET.get('q')
    if query:
        farmers = FarmerProfile.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(area__icontains=query) |
            Q(crops__name__icontains=query)
        ).filter(is_approved=True).distinct()
    else:
        farmers = FarmerProfile.objects.filter(is_approved=True)

    # Fetch accurate live data for the homepage stats
    total_farmers = FarmerProfile.objects.filter(is_approved=True).count()

    # We add a base multiplier (e.g., 150) to customers so the site looks busy even when new
    actual_customers = CustomerProfile.objects.count()
    total_customers = actual_customers + 150  # Remove "+ 150" if you want the exact raw DB count

    satisfaction_rate = 98  # You can leave this static or calculate it from a Review model later

    # Fetch the site settings
    contact_settings = SiteSetting.objects.first()

    context = {
        'farmers': farmers,
        'query': query,
        'total_farmers': total_farmers,
        'total_customers': total_customers,
        'satisfaction_rate': satisfaction_rate,
        # === THIS IS THE FIX: Pass it to the template ===
        'contact_settings': contact_settings,
    }

    return render(request, 'main_app/home.html', context)

def register(request):
    return render(request, 'main_app/register.html')

def register_farmer(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = FarmerProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            # 1. Create the user account but don't save to DB yet
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            # 2. Link the profile to the newly created user
            profile = profile_form.save(commit=False)
            profile.user = user

            # === THE CRUCIAL FIXES: Grabbing the manual fields ===
            # This ensures your custom dropdowns and number inputs are saved correctly!
            profile.area = request.POST.get('area', '')       # Catches the City
            profile.state = request.POST.get('state', '')     # Catches the State
            profile.land_area = request.POST.get('land_area', 0.00) # Catches the Acres

            profile.save()

            # 3. Direct to the pending page to wait for Admin verification
            return render(request, 'main_app/registration_pending.html')
    else:
        user_form = UserForm()
        profile_form = FarmerProfileForm()

    return render(request, 'main_app/register_farmer.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


def register_customer(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = CustomerProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            login(request, user)
            return redirect('home')
    else:
        user_form = UserForm()
        profile_form = CustomerProfileForm()
    return render(request, 'main_app/register_customer.html', {'user_form': user_form, 'profile_form': profile_form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def login_success(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    elif hasattr(request.user, 'farmerprofile'):
        return redirect('farmer_dashboard')
    else:
        return redirect('home')


# --- 2. FARMER DASHBOARD ---

@never_cache
@login_required(login_url='login')
def farmer_dashboard(request):
    """
    Renders the Farmer Dashboard with Stats, Orders, Messages, Return Requests, and Settings.
    """
    try:
        # Note: adjust this to match your actual FarmerProfile import/attribute
        farmer = request.user.farmerprofile
    except:
        return redirect('home')

    # === ADDED: POST REQUEST HANDLING FOR SETTINGS & CHAT ===
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # 1. Handle Live Chat Messages (Farmer to Customer)
        if action_type == 'send_chat_message':
            recipient_username = request.POST.get('recipient')
            message_text = request.POST.get('message')

            try:
                from main_app.models import ChatMessage
                from django.contrib.auth.models import User

                # Find the customer user
                customer_user = User.objects.get(username=recipient_username)

                # Save the message
                ChatMessage.objects.create(
                    sender=request.user,
                    receiver=customer_user,
                    message=message_text
                )
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # 2. Handle Profile Updates
        elif action_type == 'update_profile':
            request.user.first_name = request.POST.get('first_name', request.user.first_name)
            request.user.last_name = request.POST.get('last_name', request.user.last_name)
            request.user.email = request.POST.get('email', request.user.email)
            request.user.save()

            farmer.phone_no = request.POST.get('phone', getattr(farmer, 'phone_no', ''))
            farmer.area = request.POST.get('address', farmer.area)
            farmer.land_area = request.POST.get('land_area', getattr(farmer, 'land_area', 0.0))
            farmer.bio = request.POST.get('bio', getattr(farmer, 'bio', ''))

            if 'profile_photo' in request.FILES:
                farmer.profile_photo = request.FILES['profile_photo']

            farmer.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('farmer_dashboard')

        # 3. Handle Password Changes
        elif action_type == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if request.user.check_password(current_password):
                if new_password == confirm_password:
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Password securely changed!')
                else:
                    messages.error(request, 'New passwords do not match.')
            else:
                messages.error(request, 'Incorrect current password.')
            return redirect('farmer_dashboard')

    # === YOUR ORIGINAL CODE REMAINS EXACTLY THE SAME BELOW ===

    # Optional: Import your models here if not imported globally at the top of views.py
    from main_app.models import DailyStats, Crop, Order, ChatMessage, ActivityLog

    # 1. Update Daily Stats
    stats, _ = DailyStats.objects.get_or_create(farmer=farmer, date=timezone.now().date())
    stats.visitor_count += 1
    stats.save()

    # 2. Basic Queries
    crops = Crop.objects.filter(farmer=farmer)
    orders = Order.objects.filter(farmer=farmer).order_by('-date_ordered')

    # --- Fetch Return Requests ---
    return_requests = orders.filter(status='Return Requested')

    # --- Sort Orders (UPDATED TO HANDLE CANCELLATIONS) ---
    # Moved 'Cancelled' out of active and into delivered/history
    active_orders = orders.exclude(
        status__in=['Delivered', 'Returned', 'Return Rejected', 'Return Requested', 'Cancelled'])
    delivered_orders = orders.filter(status__in=['Delivered', 'Returned', 'Return Rejected', 'Cancelled'])

    # 3. Messages (Ensure this uses ChatMessage)
    client_messages = ChatMessage.objects.filter(receiver=request.user).order_by('-created_at')

    # 4. Revenue
    total_revenue = delivered_orders.filter(status='Delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0

    # 5. Charts Data Logic
    sales_labels = []
    sales_data = []
    for o in delivered_orders.filter(status='Delivered').order_by('date_ordered')[:7]:
        sales_labels.append(o.date_ordered.strftime("%d %b"))
        sales_data.append(float(o.total_price))

    # 6. Context Dictionary
    context = {
        'farmer': farmer,
        'crops': crops,
        'return_requests': return_requests,
        'active_orders': active_orders,
        'delivered_orders': delivered_orders,
        'client_messages': client_messages,
        'total_revenue': total_revenue,
        'visitors_today': stats.visitor_count,
        'percent_change': "+12.5",
        'activities': ActivityLog.objects.filter(farmer=farmer).order_by('-timestamp')[:5],
        'sales_labels_json': json.dumps(sales_labels),
        'sales_data_json': json.dumps(sales_data),
        'inventory_labels': json.dumps([c.name for c in crops]),
        'inventory_stock': json.dumps([c.quantity_kg for c in crops]),
        'recommendation': "Soil moisture is good. Suggest harvesting tomatoes soon.",
        'upcoming_tasks': [{'title': 'Water Crops', 'date': timezone.now(), 'type': 'sowing'}]
    }
    return render(request, 'main_app/farmer_dashboard.html', context)

@login_required
def add_crop(request):
    farmer = request.user.farmerprofile
    if request.method == 'POST':
        form = CropForm(request.POST, request.FILES)
        if form.is_valid():
            crop = form.save(commit=False)
            crop.farmer = farmer
            crop.save()
            ActivityLog.objects.create(farmer=farmer, title=f"Added {crop.name}", activity_type="alert")
            return redirect('farmer_dashboard')
    else:
        form = CropForm()
    return render(request, 'main_app/add_crop.html', {'form': form})


@login_required
def edit_crop(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id, farmer=request.user.farmerprofile)
    if request.method == 'POST':
        form = CropForm(request.POST, request.FILES, instance=crop)
        if form.is_valid():
            form.save()
            return redirect('farmer_dashboard')
    else:
        form = CropForm(instance=crop)
    return render(request, 'main_app/edit_crop.html', {'form': form})


@login_required
def delete_crop(request, crop_id):
    # Ensure only the owner can delete
    crop = get_object_or_404(Crop, id=crop_id, farmer=request.user.farmerprofile)
    crop.delete()
    messages.success(request, "Item deleted successfully.")
    return redirect('farmer_dashboard')


def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')

        # === WALLET REFUND LOGIC ===
        if order.status == 'Cancellation Requested' and new_status == 'Cancelled':
            customer_profile = order.customer
            if customer_profile.wallet_balance is None:
                customer_profile.wallet_balance = Decimal('0.00')

            # Add the refunded amount back to the customer's wallet
            customer_profile.wallet_balance += Decimal(str(order.total_price))
            customer_profile.save()
            messages.success(request, f'Order Cancelled. ₹{order.total_price} refunded to customer.')
        else:
            messages.success(request, f'Order status updated to {new_status}.')

        order.status = new_status
        order.save()

    return redirect('farmer_dashboard')


@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, farmer=request.user.farmerprofile)
    order.delete()
    return redirect('farmer_dashboard')


@login_required
def send_suggestion(request):
    if request.method == 'POST':
        Suggestion.objects.create(farmer=request.user.farmerprofile, message=request.POST.get('message'))
        messages.success(request, "Message sent to Admin.")
    return redirect('farmer_dashboard')


# --- 3. SHOPPING & CART ---

def farmer_shop(request, farmer_id):
    farmer = get_object_or_404(FarmerProfile, id=farmer_id)
    return render(request, 'main_app/farmer_shop.html', {'farmer': farmer, 'crops': farmer.crops.all()})


def send_farmer_message(request, farmer_id):
    if request.method == "POST":
        farmer = get_object_or_404(FarmerProfile, id=farmer_id)
        FarmerMessage.objects.create(
            farmer=farmer,
            sender_name=request.POST.get('name'),
            sender_contact=request.POST.get('contact'),
            message=request.POST.get('message')
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def checkout(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id)
    return render(request, 'main_app/checkout.html', {'crop': crop})


@login_required
def confirm_payment(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id)
    if request.method == 'POST':
        qty = float(request.POST.get('quantity', 1))
        total = Decimal(qty) * crop.price_per_kg
        order = Order.objects.create(
            customer=request.user.customerprofile,
            farmer=crop.farmer,
            crop=crop,
            quantity=qty,
            total_price=total,
            status='Pending'
        )
        crop.quantity_kg -= qty
        crop.save()
        return redirect('order_success', order_id=order.id)
    return redirect('home')


# --- CART LOGIC (With AJAX Support) ---

def view_cart(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(customer=request.user.customerprofile)
        total = sum(item.total_price() for item in items)
        return render(request, 'main_app/cart.html', {'cart_items': items, 'grand_total': total})
    else:
        return redirect('login')


@login_required
def add_to_cart(request, crop_id):
    if request.method == 'POST':
        crop = get_object_or_404(Crop, id=crop_id)
        try:
            customer = request.user.customerprofile
        except:
            return JsonResponse({'success': False, 'message': 'Only Customers can shop!'})

        quantity = float(request.POST.get('quantity', 1))

        # Update DB
        item, created = CartItem.objects.get_or_create(customer=customer, crop=crop)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        # Update Session for Badge
        cart = request.session.get('cart_items', {})
        cart[str(crop_id)] = cart.get(str(crop_id), 0) + quantity
        request.session['cart_items'] = cart
        request.session.modified = True

        return JsonResponse({'success': True, 'cart_count': len(cart)})

    return redirect('home')


@login_required
def remove_from_cart(request, crop_id):
    CartItem.objects.filter(customer=request.user.customerprofile, crop_id=crop_id).delete()

    # Update Session
    cart = request.session.get('cart_items', {})
    if str(crop_id) in cart:
        del cart[str(crop_id)]
        request.session['cart_items'] = cart
        request.session.modified = True

    return redirect('view_cart')


@login_required
def cart_checkout(request):
    items = CartItem.objects.filter(customer=request.user.customerprofile)
    total = sum(item.total_price() for item in items)
    return render(request, 'main_app/cart_checkout.html', {'cart_items': items, 'grand_total': total})


@login_required
def process_cart(request):
    customer = request.user.customerprofile
    items = CartItem.objects.filter(customer=customer)
    if not items: return redirect('home')

    orders = []
    total = 0
    for item in items:
        order = Order.objects.create(
            customer=customer, farmer=item.crop.farmer, crop=item.crop,
            quantity=item.quantity, total_price=item.total_price(), status='Pending'
        )
        orders.append(order)
        total += item.total_price()
        item.crop.quantity_kg -= item.quantity
        item.crop.save()

    items.delete()  # Clear cart
    request.session['cart_items'] = {}  # Clear session badge

    return render(request, 'main_app/invoice.html',
                  {'orders': orders, 'grand_total': total, 'date': timezone.now(), 'customer': customer})


# --- 4. CUSTOMER ORDERS ---

@login_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user.customerprofile).order_by('-date_ordered')
    return render(request, 'main_app/my_orders.html', {'orders': orders})


@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user.customerprofile)
    return render(request, 'main_app/track_order.html', {'order': order})


@login_required
def download_bill(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'main_app/bill.html', {'order': order})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'main_app/order_success.html', {'order': order, 'grand_total': order.total_price})


@login_required
def profile_settings(request):
    user = request.user
    if hasattr(user, 'farmerprofile'):
        profile = user.farmerprofile
        PForm = FarmerProfileUpdateForm
    else:
        profile = user.customerprofile
        PForm = CustomerProfileUpdateForm

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = PForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Profile Updated")
            return redirect('profile_settings')
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = PForm(instance=profile)
    return render(request, 'main_app/profile_settings.html', {'u_form': u_form, 'p_form': p_form})


# --- 5. ADMIN ---


@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    farmers = FarmerProfile.objects.all()
    customers = CustomerProfile.objects.all()
    orders = Order.objects.all()

    total_farmers = farmers.count()
    total_customers = customers.count()
    total_orders = orders.count()

    revenue_agg = orders.aggregate(Sum('total_price'))
    total_revenue = revenue_agg['total_price__sum'] or 0

    pending_approvals = farmers.filter(is_approved=False).count()
    pending_payouts_count = Payout.objects.filter(status='Pending').count()
    payout_requests = Payout.objects.filter(status='Pending')
    suggestions = Suggestion.objects.all().order_by('-date_sent')

    # === THE FIX IS HERE ===
    # Use singular SiteSetting and .first() so it perfectly matches the homepage!
    site_settings = SiteSetting.objects.first()

    recent_orders = orders.order_by('-id')[:5]
    ph_requests = PHTestRequest.objects.filter(status='Pending').order_by('booking_date')

    # Calculate Top Selling Crops
    top_crops = Crop.objects.annotate(
        total_sold=Sum('order__quantity')
    ).filter(total_sold__gt=0).order_by('-total_sold')[:3]

    # === 1. NEW: DYNAMIC REVENUE CHART LOGIC ===
    current_year = timezone.now().year
    monthly_revenue = orders.filter(date_ordered__year=current_year).annotate(
        month=TruncMonth('date_ordered')
    ).values('month').annotate(
        total=Sum('total_price')
    ).order_by('month')

    months_data = {i: 0 for i in range(1, 13)}
    for entry in monthly_revenue:
        if entry['month']:
            months_data[entry['month'].month] = float(entry['total'] or 0)

    chart_labels = [calendar.month_abbr[i].upper() for i in range(1, 13)]
    chart_data = [months_data[i] for i in range(1, 13)]

    # === 2. NEW: GLOBAL INVENTORY OVERSIGHT ===
    all_crops = Crop.objects.all().order_by('-id')

    # === 3. NEW: DUE SUBSIDIES CALCULATION ===
    # Checks if any farmer's next scheduled subsidy date is today or in the past
    due_subsidies_count = FarmerProfile.objects.filter(next_subsidy_date__lte=timezone.now().date()).count()

    # === 4. NEW: DYNAMIC PAYOUTS & SUBSIDIES TRACKING ===
    # Find all farmers who have been granted a subsidy (they have a next_subsidy_date)
    active_subsidies = FarmerProfile.objects.filter(next_subsidy_date__isnull=False)
    active_subsidies_count = active_subsidies.count()

    # Calculate real total disbursed (Active Subsidies * ₹5,000)
    total_disbursed = active_subsidies_count * 5000

    context = {
        'farmers': farmers,
        'customers': customers,
        'total_farmers': total_farmers,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_approvals': pending_approvals,
        'pending_payouts_count': pending_payouts_count,
        'payout_requests': payout_requests,
        'suggestions': suggestions,
        'recent_orders': recent_orders,
        'site_settings': site_settings,
        'ph_requests': ph_requests,
        'top_crops': top_crops,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
        'all_crops': all_crops,
        'due_subsidies_count': due_subsidies_count,  # Passed to Notifications Bell
        'active_subsidies': active_subsidies,  # Passed to Payouts Tab table
        'active_subsidies_count': active_subsidies_count,  # Passed to Payouts Tab KPI
        'total_disbursed': total_disbursed,  # Passed to Payouts Tab KPI
    }
    return render(request, 'main_app/admin_dashboard.html', context)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_crop(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id)
    crop.delete()
    messages.success(request, f'Listing "{crop.name}" has been removed from the platform.')
    return redirect('admin_dashboard')


# 2. FIND YOUR SUBMIT FUNCTION AT THE BOTTOM AND REPLACE IT WITH THIS:
@login_required
def submit_ph_request(request):
    """ Receives the Farmer's form and saves it to the database """
    if request.method == 'POST':
        farmer = request.user.farmerprofile

        booking_date = request.POST.get('booking_date')
        if not booking_date:
            booking_date = None  # Prevent database error if date is empty

        PHTestRequest.objects.create(
            farmer=farmer,
            contact_number=request.POST.get('contact_number'),
            sampling_location=request.POST.get('sampling_location'),
            notes=request.POST.get('notes'),
            soil_photo=request.FILES.get('soil_photo'),
            booking_date=booking_date,
            booking_time=request.POST.get('booking_time'),
            assigned_agent=request.POST.get('assigned_agent')
        )
        return redirect('farmer_dashboard')
    return redirect('farmer_dashboard')


@login_required
def update_ph_level(request, req_id):
    """ Admin inputs the final lab result and updates the farmer's profile """
    if request.method == 'POST' and request.user.is_superuser:
        ph_req = get_object_or_404(PHTestRequest, id=req_id)
        ph_result = request.POST.get('ph_result')

        # 1. Update the Farmer's permanent profile
        farmer = ph_req.farmer
        farmer.soil_ph_level = ph_result
        farmer.save()

        # 2. Mark this request ticket as Completed
        ph_req.status = 'Completed'
        ph_req.save()

        # 3. Create a live activity alert for the farmer
        ActivityLog.objects.create(
            farmer=farmer,
            title=f"Admin updated Soil pH to {ph_result}",
            activity_type="alert"
        )

        messages.success(request, f"pH level for {farmer.user.first_name} updated successfully!")
    return redirect('admin_dashboard')

@user_passes_test(lambda u: u.is_superuser)
def approve_farmer(request, id):
    f = get_object_or_404(FarmerProfile, id=id)
    f.is_approved = True
    f.save()
    return redirect('admin_dashboard')


@user_passes_test(lambda u: u.is_superuser)
def reject_farmer(request, id):
    get_object_or_404(FarmerProfile, id=id).user.delete()
    return redirect('admin_dashboard')


@user_passes_test(lambda u: u.is_superuser)
def delete_farmer(request, farmer_id):
    get_object_or_404(FarmerProfile, id=farmer_id).user.delete()
    return redirect('admin_dashboard')


@user_passes_test(lambda u: u.is_superuser)
def update_farmer_details(request, farmer_id):
    f = get_object_or_404(FarmerProfile, id=farmer_id)
    f.weather_update = request.POST.get('weather_update')
    f.soil_ph_level = request.POST.get('soil_ph_level')
    f.save()
    return redirect('admin_dashboard')


@user_passes_test(lambda u: u.is_superuser)
def delete_suggestion(request, id):
    get_object_or_404(Suggestion, id=id).delete()
    return redirect('admin_dashboard')


@login_required
@require_POST
def delete_messages(request):
    # 1. Grab the list of message IDs sent from the HTML button
    message_ids = request.POST.getlist('message_ids')

    if not message_ids:
        messages.error(request, "Error: No messages selected to delete.")
        return redirect(reverse('farmer_dashboard') + '#messages')

    try:
        # 2. PERFORM THE DELETE using the correct model (ChatMessage)
        # Note: We filter by receiver=request.user to ensure farmers can only delete messages sent TO them.
        deleted_count, _ = ChatMessage.objects.filter(
            id__in=message_ids,
            receiver=request.user
        ).delete()

        # 3. Check if it actually deleted anything
        if deleted_count > 0:
            messages.success(request, f"Successfully deleted {deleted_count} message(s).")
        else:
            messages.warning(request,
                             "No messages were deleted. They may have already been removed or you don't have permission to delete them.")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    # 4. Redirect back to the messages tab
    return redirect(reverse('farmer_dashboard') + '#messages')
@login_required
def add_farm_task(request):
    if request.method == "POST":
        title = request.POST.get('title')
        task_type = request.POST.get('type')

        ActivityLog.objects.create(
            farmer=request.user.farmerprofile,
            title=f"Scheduled Task: {title}",
            activity_type=task_type
        )
        messages.success(request, "Task added to calendar!")
        return redirect('farmer_dashboard')
    return redirect('farmer_dashboard')


@login_required
def update_farmer_settings(request):
    if request.method == 'POST':
        farmer = request.user.farmerprofile
        user = request.user

        # Update User details
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        # Update FarmerProfile details
        farmer.phone_number = request.POST.get('phone')
        farmer.area = request.POST.get('address')
        farmer.bio = request.POST.get('bio')

        # === THIS IS THE MISSING PIECE ===
        # Catch the land area from the form and save it to the database
        land_area_input = request.POST.get('land_area')
        if land_area_input:
            farmer.land_area = land_area_input
        # ==================================

        if 'profile_photo' in request.FILES:
            farmer.profile_photo = request.FILES['profile_photo']

        farmer.save()
        messages.success(request, 'Profile updated successfully!')

    return redirect(reverse('farmer_dashboard') + '#settings')

@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        current_pass = request.POST.get('current_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        if not user.check_password(current_pass):
            messages.error(request, "Incorrect current password.")
            return redirect('farmer_dashboard')

        if new_pass != confirm_pass:
            messages.error(request, "New passwords do not match.")
            return redirect('farmer_dashboard')

        user.set_password(new_pass)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, "Password updated successfully!")
        return redirect('farmer_dashboard')

    return redirect('farmer_dashboard')




@login_required
def customer_dashboard(request):
    try:
        customer = request.user.customerprofile
    except:
        return redirect('home')

    # === POST REQUEST HANDLING FOR ALL DASHBOARD ACTIONS ===
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # 1. Save Account Details & Profile Photo
        if action_type == 'update_profile':
            request.user.username = request.POST.get('username')
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.email = request.POST.get('email')
            request.user.save()

            # Save profile photo if a new one was uploaded
            if 'profile_photo' in request.FILES:
                request.user.customerprofile.profile_photo = request.FILES['profile_photo']
                request.user.customerprofile.save()

            messages.success(request, 'Account details updated successfully!')
            return redirect('customer_dashboard')

        # 2. Save New Password
        elif action_type == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if request.user.check_password(old_password):
                if new_password == confirm_password:
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Password securely changed!')
                else:
                    messages.error(request, 'New passwords do not match. Try again.')
            else:
                messages.error(request, 'Incorrect current password.')
            return redirect('customer_dashboard')

        # 3. Save Delivery Address
        elif action_type == 'update_address':
            profile = request.user.customerprofile
            profile.address = request.POST.get('address')
            profile.city = request.POST.get('city')
            profile.state = request.POST.get('state')
            profile.pincode = request.POST.get('pincode')
            profile.phone_number = request.POST.get('phone_number')
            profile.save()

            messages.success(request, 'Delivery address saved successfully!')
            return redirect('customer_dashboard')

        # 4. Handle Wallet Top-Up
        elif action_type == 'top_up_wallet':
            amount = request.POST.get('amount')
            if amount and float(amount) > 0:
                profile = request.user.customerprofile

                # Safely ensure current balance is a Decimal before doing math
                current_balance = profile.wallet_balance if profile.wallet_balance is not None else Decimal('0.00')

                # Add the new amount to the current balance and save
                profile.wallet_balance = current_balance + Decimal(str(amount))
                profile.save()

                messages.success(request, f'Successfully topped up ₹{amount} to your wallet!')
            else:
                messages.error(request, 'Invalid top-up amount.')
            return redirect('customer_dashboard')

        # 5. Handle Order Cancellation Request
        elif action_type == 'request_cancellation':
            order_id = request.POST.get('order_id')
            try:
                from main_app.models import Order
                order = Order.objects.get(id=order_id, customer=request.user.customerprofile)

                if order.status == 'Pending':
                    order.status = 'Cancellation Requested'
                    order.save()
                    messages.success(request, 'Cancellation request sent to farmer for approval.')
                else:
                    messages.error(request, 'This order cannot be cancelled as it is already being processed.')
            except Exception as e:
                messages.error(request, 'Order not found.')
            return redirect('customer_dashboard')

        # 6. Handle Order Return Request
        elif action_type == 'request_return':
            order_id = request.POST.get('order_id')
            try:
                from main_app.models import Order
                order = Order.objects.get(id=order_id, customer=request.user.customerprofile)
                if order.status == 'Delivered':
                    order.status = 'Return Requested'
                    order.save()
                    messages.success(request, 'Return request submitted successfully. We will arrange a pickup.')
                else:
                    messages.error(request, 'Only delivered orders can be returned.')
            except Exception as e:
                messages.error(request, 'Order not found.')
            return redirect('customer_dashboard')

        # 7. Handle Live Chat Messages
        elif action_type == 'send_chat_message':
            recipient_username = request.POST.get('recipient')
            message_text = request.POST.get('message')

            try:
                from main_app.models import ChatMessage  # Imported exactly as named in models.py

                # Find the farmer the customer selected
                farmer_user = User.objects.get(username=recipient_username)

                # CREATE and SAVE the message so it shows on the farmer dashboard
                ChatMessage.objects.create(
                    sender=request.user,
                    receiver=farmer_user,
                    message=message_text
                )
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

    # === BASE DASHBOARD QUERIES & CONTEXT ===
    from main_app.models import Order
    orders = Order.objects.filter(customer=customer).order_by('-date_ordered')
    delivered_count = orders.filter(status='Delivered').count()

    # Calculate Total Amount Spent (excluding cancelled orders)
    total_spent = sum(order.total_price for order in orders if order.status != 'Cancelled')

    # Get a unique list of farmers the customer has bought from for the chat dropdown
    farmer_set = set()
    for order in orders:
        if order.farmer and order.farmer.user:
            farmer_set.add(order.farmer.user)

    farmers = list(farmer_set)

    context = {
        'orders': orders,
        'delivered_count': delivered_count,
        'farmers': farmers,
        'total_spent': total_spent,  # Included in context so the HTML displays it!
    }

    return render(request, 'main_app/customer_dashboard.html', context)

@login_required
def request_return(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id, customer=request.user.customerprofile)
        reason = request.POST.get('reason')
        order.status = 'Return Requested'
        order.return_reason = reason
        order.save()
    return redirect('customer_dashboard')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = CustomerProfileUpdateForm(request.POST, request.FILES, instance=request.user.customerprofile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('customer_dashboard')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = CustomerProfileUpdateForm(instance=request.user.customerprofile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'main_app/edit_profile.html', context)


@login_required
def send_chat_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            msg_text = data.get('message')
            recipient_username = data.get('recipient')

            if not msg_text or not recipient_username:
                return JsonResponse({'success': False, 'error': 'Missing data'})

            try:
                farmer_user = User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Farmer not found'})

            ChatMessage.objects.create(
                sender=request.user,
                receiver=farmer_user,
                message=msg_text
            )

            return JsonResponse({'success': True, 'message': f'Sent to {recipient_username}'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def update_address(request):
    if request.method == 'POST':
        try:
            profile = request.user.customerprofile
            profile.address = request.POST.get('address')
            profile.city = request.POST.get('city')
            profile.state = request.POST.get('state')
            profile.pincode = request.POST.get('pincode')
            profile.phone_number = request.POST.get('phone_number')
            profile.save()
            messages.success(request, "Delivery address updated successfully!") # NEW
        except Exception as e:
            print(e)
            messages.error(request, "Failed to update address. Please try again.") # NEW
    return redirect('customer_dashboard')


@login_required
def process_return(request, order_id, action):
    """
    Handles the Farmer accepting or rejecting a return request.
    Action must be 'approve' or 'reject'.
    """
    order = get_object_or_404(Order, id=order_id, farmer=request.user.farmerprofile)

    if action == 'approve':
        order.status = 'Returned'
        print(f"Order #{order.id} return APPROVED.")

    elif action == 'reject':
        order.status = 'Return Rejected'
        print(f"Order #{order.id} return REJECTED.")

    order.save()
    return redirect('farmer_dashboard')


def update_settings(request):
    if request.method == "POST":
        settings, created = SiteSettings.objects.get_or_create(id=1)
        settings.announcement = request.POST.get('announcement')
        settings.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        settings.save()

    return redirect('admin_dashboard')


# --- CROP PREDICTION VIEW ---
def crop_prediction(request):
    recommendation = None
    image_url = None

    if request.method == 'POST':
        # 1. Get Data from Form
        try:
            N = float(request.POST.get('nitrogen'))
            P = float(request.POST.get('phosphorus'))
            K = float(request.POST.get('potassium'))
            ph = float(request.POST.get('ph'))
            rainfall = float(request.POST.get('rainfall'))

            # 2. "AI" Logic (Simplified Rule-Based System for Demo)

            if N > 80 and P > 40 and K > 40:
                if rainfall > 200:
                    recommendation = "Rice"
                    image_url = "https://images.unsplash.com/photo-1536617621272-9359dc235c36?q=80&w=1000"
                else:
                    recommendation = "Corn (Maize)"
                    image_url = "https://images.unsplash.com/photo-1551754655-cd27e38d2076?q=80&w=1000"

            elif ph < 5.5:  # Acidic Soil
                recommendation = "Tea or Coffee"
                image_url = "https://images.unsplash.com/photo-1579888944880-d98341245702?q=80&w=1000"

            elif ph > 7.5:  # Alkaline Soil
                recommendation = "Chickpea or Barley"
                image_url = "https://images.unsplash.com/photo-1518994603110-1751938d9121?q=80&w=1000"

            elif rainfall < 50:  # Dry Weather
                recommendation = "Watermelon or Muskmelon"
                image_url = "https://images.unsplash.com/photo-1587049352846-4a222e784d38?q=80&w=1000"

            elif rainfall > 150 and 20 < float(request.POST.get('temperature', 25)) < 30:
                recommendation = "Jute"
                image_url = "https://t4.ftcdn.net/jpg/02/33/27/36/360_F_233273663_UqXn9K9k9k9k9k9k.jpg"

            else:
                # Default Logic based on general NPK
                if K > P:
                    recommendation = "Grapes or Bananas"
                    image_url = "https://images.unsplash.com/photo-1537640538965-1756e1759066?q=80&w=1000"
                else:
                    recommendation = "Tomatoes or Vegetables"
                    image_url = "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?q=80&w=1000"

        except ValueError:
            recommendation = "Error: Please enter valid numbers."

    context = {
        'recommendation': recommendation,
        'image_url': image_url
    }
    return render(request, 'main_app/crop_predict.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def grant_subsidy(request, farmer_id):
    if request.method == 'POST':
        farmer = get_object_or_404(FarmerProfile, id=farmer_id)
        next_date = request.POST.get('next_subsidy_date')

        if farmer.land_area >= 5:
            subsidy_amount = Decimal('5000.00')
            farmer.wallet_balance += subsidy_amount
            farmer.next_subsidy_date = next_date  # Saves the scheduled date!
            farmer.save()
            messages.success(request, f"₹{subsidy_amount} Subsidy credited and next cycle scheduled for {next_date}.")
        else:
            messages.error(request, "Farmer does not meet the minimum requirement.")

    return redirect('admin_dashboard')
def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)


def update_admin_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        # --- THE FIX: Create the profile if it doesn't exist! ---
        if 'profile_photo' in request.FILES:
            try:
                # Try to get the existing profile
                profile = user.adminprofile
            except ObjectDoesNotExist:
                # If it doesn't exist, create it right now!
                profile = AdminProfile.objects.create(user=user)

            # Now save the uploaded image
            profile.profile_photo = request.FILES['profile_photo']
            profile.save()
        # --------------------------------------------------------

        messages.success(request, 'Profile updated successfully!')
        return redirect('admin_dashboard')
    return redirect('admin_dashboard')


def update_admin_password(request):
    if request.method == 'POST':
        user = request.user
        old_pass = request.POST.get('old_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        if not user.check_password(old_pass):
            messages.error(request, 'Incorrect current password.')
        elif new_pass != confirm_pass:
            messages.error(request, 'New passwords do not match.')
        else:
            user.set_password(new_pass)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')

        return redirect('admin_dashboard')
    return redirect('admin_dashboard')




@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def update_site_settings(request):
    if request.method == 'POST':
        # FIXED: Using SiteSetting (Singular) to match your models.py!
        settings, created = SiteSetting.objects.get_or_create(id=1)

        # Update the object with data from the form
        settings.location = request.POST.get('location', settings.location)
        settings.email = request.POST.get('email', settings.email)
        settings.phone = request.POST.get('phone', settings.phone)
        settings.working_hours = request.POST.get('working_hours', settings.working_hours)

        # Save to the database
        settings.save()

        # Send a success notification to the UI
        messages.success(request, "Contact Us details updated successfully!")

    # Dynamically redirect back to the admin dashboard and trigger the #settings tab
    return redirect(reverse('admin_dashboard') + '#settings')


@login_required
def delete_customer(request, customer_id):
    try:
        # Find the specific customer
        customer = CustomerProfile.objects.get(id=customer_id)

        # Delete the base User account (this will automatically delete the CustomerProfile too)
        user_to_delete = customer.user
        user_to_delete.delete()

        messages.success(request, f"Consumer {customer.user.first_name} has been permanently deleted.")
    except CustomerProfile.DoesNotExist:
        messages.error(request, "Error: Could not find that consumer in the database.")

    # Redirect back to the admin dashboard, staying on the customers tab
    return redirect(reverse('admin_dashboard') + '#customers')


def register_customer(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = CustomerProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            # 1. Create the user account but don't save to DB yet
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            # 2. Link the profile to the newly created user
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            # REMOVED: login(request, user) -> This forces them to log in manually!

            # 3. Direct the browser to show the beautiful Success Animation screen
            return render(request, 'main_app/register_customer.html', {'registration_successful': True})

    else:
        user_form = UserForm()
        profile_form = CustomerProfileForm()

    return render(request, 'main_app/register_customer.html', {'user_form': user_form, 'profile_form': profile_form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_ph_request(request, req_id):
    if request.method == 'POST':
        # Find the specific request and delete it
        ph_req = get_object_or_404(PHTestRequest, id=req_id)
        ph_req.delete()
        messages.success(request, "pH test request deleted successfully.")

    # Redirect back to the admin dashboard (the JS hash will keep it on the phtests tab)
    return redirect('admin_dashboard')


def apply_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Get the discount (e.g., 0.05 for 5%)
            discount = float(data.get('discount', 0))

            # Save it to the user's session so it carries over to checkout!
            request.session['cart_discount'] = discount

            return JsonResponse({'success': True, 'discount': discount})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})