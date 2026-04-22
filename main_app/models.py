from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone



# --- 1. PROFILES ---
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customerprofile')
    phone_number = models.CharField(max_length=15)
    profile_photo = models.ImageField(upload_to='customer_profiles/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return self.user.username


class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmerprofile')
    phone_no = models.CharField(max_length=15)
    area = models.CharField(max_length=100)
    profile_photo = models.ImageField(upload_to='farmer_photos/', blank=True, null=True)
    id_proof = models.FileField(upload_to='farmer_proofs/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    # New Profile Field for the Settings/Modal
    bio = models.TextField(blank=True, null=True)

    # NEW: Subsidy & Wallet Fields
    land_area = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Land area in acres")
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Dashboard Widgets
    weather_update = models.CharField(max_length=50, default="28°C")

    # ---> UPDATED: Default is now 0.0 so they must request a test first <---
    soil_ph_level = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)

    next_subsidy_date = models.DateField(null=True, blank=True)

    # Helper function to easily check subsidy eligibility
    def is_eligible_for_subsidy(self):
        return self.land_area >= 5.00

    def __str__(self):
        return self.user.username


# --- 2. INVENTORY ---
class Crop(models.Model):
    CATEGORY_CHOICES = [
        ('vegetable', 'Vegetable'),
        ('fruit', 'Fruit'),
        ('grain', 'Grain'),
    ]
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='vegetable')
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_kg = models.FloatField()
    image = models.ImageField(upload_to='crop_photos/')
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# --- 3. ORDERS & CART ---
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        # New Statuses for Return Logic
        ('Return Requested', 'Return Requested'),
        ('Returned', 'Returned'),
        ('Return Rejected', 'Return Rejected'),
    ]

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='orders')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)

    # Field to store the return reason
    return_reason = models.CharField(max_length=200, blank=True, null=True)

    quantity = models.FloatField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES,
                              default='Pending')  # Increased max_length just in case
    date_ordered = models.DateTimeField(auto_now_add=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class CartItem(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    quantity = models.FloatField(default=1.0)

    def total_price(self):
        return Decimal(self.quantity) * self.crop.price_per_kg


# --- 4. ANALYTICS ---
class ActivityLog(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=50)  # 'sale', 'alert'
    timestamp = models.DateTimeField(auto_now_add=True)


class DailyStats(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    visitor_count = models.IntegerField(default=0)


class Suggestion(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)


class FarmerMessage(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    sender_name = models.CharField(max_length=100)
    sender_contact = models.CharField(max_length=15)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages", null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender.username}: {self.message[:20]}"

class SiteSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    announcement = models.TextField(default="Site is under maintenance.")

    def __str__(self):
        return "Site Settings"

class Payout(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Pending', choices=[
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Rejected', 'Rejected')
    ])
    request_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payout #{self.id} - {self.farmer.user.username}"
class Dispute(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=50, choices=[
        ('Quality Issue', 'Quality Issue'),
        ('Not Received', 'Not Received'),
        ('Damaged', 'Damaged Item'),
        ('Other', 'Other')
    ])
    description = models.TextField()
    status = models.CharField(max_length=20, default='Open', choices=[
        ('Open', 'Open'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispute #{self.id} for Order #{self.order.id}"


class PHTestRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed')
    ]

    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='ph_requests')
    contact_number = models.CharField(max_length=20)
    sampling_location = models.CharField(max_length=255)
    soil_photo = models.ImageField(upload_to='ph_samples/')
    notes = models.TextField(blank=True, null=True)

    # Booking Allocations
    booking_date = models.DateField(blank=True, null=True)
    booking_time = models.CharField(max_length=50, blank=True, null=True)
    assigned_agent = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"pH Request: {self.farmer.user.username} - {self.sampling_location}"

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to='admin_photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"
class SiteSetting(models.Model):
    location = models.CharField(max_length=255, default="Kerala, India")
    email = models.EmailField(default="support@efarming.com")
    phone = models.CharField(max_length=20, default="+91 98765 43210")
    working_hours = models.CharField(max_length=100, default="Mon-Sun: 7AM - 10PM")

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Contact Info Settings"