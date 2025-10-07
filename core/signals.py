# """
# Django signals for handling tenant schema creation.
# """
#
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.db import transaction
# from .models import Client
# import threading
# import time
#
#
# def create_tenant_schema_async(client_id):
#     """Async function to create tenant schema after transaction completes"""
#     # Wait a bit to ensure the transaction is committed
#     time.sleep(1)
#
#     try:
#         client = Client.objects.get(id=client_id)
#         if not client.schema_exists():
#             # Create schema
#             client.create_schema(check_if_exists=True)
#
#             # Run migrations
#             from django.core.management import call_command
#             call_command('migrate_schemas', schema_name=client.schema_name, verbosity=0)
#
#             print(f"✅ Schema created successfully for: {client.name} ({client.schema_name})")
#         else:
#             print(f"ℹ️  Schema already exists for: {client.name} ({client.schema_name})")
#
#     except Exception as e:
#         print(f"❌ Error creating schema: {e}")
#
#
# @receiver(post_save, sender=Client)
# def handle_client_creation(sender, instance, created, **kwargs):
#     """Handle client creation by creating schema in background"""
#     if created:
#         # Create schema in a separate thread to avoid transaction conflicts
#         schema_thread = threading.Thread(
#             target=create_tenant_schema_async,
#             args=(instance.id,)
#         )
#         schema_thread.daemon = True
#         schema_thread.start()