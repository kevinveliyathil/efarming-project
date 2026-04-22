from django.contrib import admin
from .models import FarmerProfile, CustomerProfile, Crop, Order, Suggestion, FarmerMessage, SiteSetting

# Custom Admin for Farmer to handle Approvals easily
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_no', 'area', 'is_approved')
    list_filter = ('is_approved', 'area')
    actions = ['approve_farmers']

    def approve_farmers(self, request, queryset):
        queryset.update(is_approved=True)
    approve_farmers.short_description = "Mark selected farmers as Approved"

# Custom Admin for Orders to see status
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'crop', 'customer', 'farmer', 'total_price', 'status', 'date_ordered')
    list_filter = ('status', 'date_ordered')

admin.site.register(FarmerProfile, FarmerProfileAdmin)
admin.site.register(CustomerProfile)
admin.site.register(Crop)
admin.site.register(Order, OrderAdmin)
admin.site.register(Suggestion)
admin.site.register(FarmerMessage)
admin.site.register(SiteSetting)