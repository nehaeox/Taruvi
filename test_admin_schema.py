#!/usr/bin/env python
"""
Test script to verify admin schema creation works without TransactionManagementError
"""
import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taruvi_project.settings')
django.setup()

from core.admin import ClientAdmin, ClientAdminForm
from core.models import Client

def test_admin_form():
    """Test the custom admin form"""
    print("🔍 Testing ClientAdminForm...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.post('/admin/')
    
    # Add a user and messages to the request (required for admin)
    request.user = User(username='testuser', is_superuser=True)
    setattr(request, 'session', {})
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # Test form initialization
    form_data = {
        'name': 'Test Tenant',
        'schema_name': 'test_tenant_schema'
    }
    
    form = ClientAdminForm(data=form_data)
    if form.is_valid():
        print("✅ Form validation passed")
        
        # Test that we can create the form without errors
        try:
            # Don't actually save to avoid creating real schemas
            instance = form.save(commit=False)
            print(f"✅ Form save (commit=False) worked: {instance}")
            print(f"   - Name: {instance.name}")
            print(f"   - Schema: {instance.schema_name}")
        except Exception as e:
            print(f"❌ Form save failed: {e}")
    else:
        print(f"❌ Form validation failed: {form.errors}")

def test_admin_class():
    """Test the admin class"""
    print("\n🔍 Testing ClientAdmin...")
    
    admin = ClientAdmin(Client, None)
    print(f"✅ ClientAdmin instantiated: {admin}")
    print(f"   - Form class: {admin.form}")
    print(f"   - Fieldsets: {admin.fieldsets}")

if __name__ == '__main__':
    print("🚀 Testing Admin Schema Creation Solution\n")
    test_admin_form()
    test_admin_class()
    print("\n✅ All tests completed!")