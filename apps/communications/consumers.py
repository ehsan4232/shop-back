import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from apps.communications.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_group_name = f'user_{self.user_id}'
        
        # Check if user is authenticated and authorized
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
            
        # Check if the user is accessing their own notifications
        if str(user.id) != str(self.user_id):
            await self.close()
            return
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user {self.user_id}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notifications'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for user {self.user_id}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'mark_read':
                notification_id = text_data_json.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
            
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user_id}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")

    async def notification_message(self, event):
        """Send notification to WebSocket"""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': {
                'id': notification['id'],
                'title': notification['title'],
                'message': notification['message'],
                'notification_type': notification.get('notification_type', 'info'),
                'timestamp': notification['timestamp'],
                'read': notification.get('read', False),
                'action': notification.get('action'),
            }
        }))

    async def order_update(self, event):
        """Send order update notification"""
        order_data = event['order']
        
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order': order_data
        }))

    async def payment_update(self, event):
        """Send payment update notification"""
        payment_data = event['payment']
        
        await self.send(text_data=json.dumps({
            'type': 'payment_update',
            'payment': payment_data
        }))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.is_read = True
            notification.save()
            logger.info(f"Marked notification {notification_id} as read for user {self.user_id}")
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")


class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time order tracking"""
    
    async def connect(self):
        """Handle WebSocket connection for order tracking"""
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.order_group_name = f'order_{self.order_id}'
        
        # Check if user is authenticated
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
            
        # Check if user has access to this order
        has_access = await self.check_order_access(user, self.order_id)
        if not has_access:
            await self.close()
            return
        
        # Join order group
        await self.channel_layer.group_add(
            self.order_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Order tracking WebSocket connected for order {self.order_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'order_group_name'):
            await self.channel_layer.group_discard(
                self.order_group_name,
                self.channel_name
            )
        logger.info(f"Order tracking WebSocket disconnected for order {self.order_id}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_status':
                # Send current order status
                order_data = await self.get_order_status(self.order_id)
                await self.send(text_data=json.dumps({
                    'type': 'order_status',
                    'order': order_data
                }))
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received for order {self.order_id}")
        except Exception as e:
            logger.error(f"Error handling order tracking message: {str(e)}")

    async def order_status_update(self, event):
        """Send order status update"""
        order_data = event['order']
        
        await self.send(text_data=json.dumps({
            'type': 'order_status_update',
            'order': order_data
        }))

    async def shipping_update(self, event):
        """Send shipping update"""
        shipping_data = event['shipping']
        
        await self.send(text_data=json.dumps({
            'type': 'shipping_update',
            'shipping': shipping_data
        }))

    @database_sync_to_async
    def check_order_access(self, user, order_id):
        """Check if user has access to the order"""
        try:
            from apps.orders.models import Order
            order = Order.objects.get(id=order_id)
            
            # User can access if they are the customer or the store owner
            if order.customer == user:
                return True
            
            # Check if user owns any store that has items in this order
            for item in order.items.all():
                if item.product_instance.product.store.owner == user:
                    return True
                    
            return False
            
        except Order.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking order access: {str(e)}")
            return False

    @database_sync_to_async
    def get_order_status(self, order_id):
        """Get current order status"""
        try:
            from apps.orders.models import Order
            order = Order.objects.select_related('customer').get(id=order_id)
            
            return {
                'id': str(order.id),
                'order_number': order.order_number,
                'status': order.status,
                'payment_status': order.payment_status,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat(),
                'tracking_number': getattr(order, 'tracking_number', None),
            }
            
        except Order.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            return None


class StoreNotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for store owner notifications"""
    
    async def connect(self):
        """Handle WebSocket connection for store notifications"""
        self.store_id = self.scope['url_route']['kwargs']['store_id']
        self.store_group_name = f'store_{self.store_id}'
        
        # Check if user is authenticated and owns the store
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
            
        has_access = await self.check_store_access(user, self.store_id)
        if not has_access:
            await self.close()
            return
        
        # Join store group
        await self.channel_layer.group_add(
            self.store_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Store notification WebSocket connected for store {self.store_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'store_group_name'):
            await self.channel_layer.group_discard(
                self.store_group_name,
                self.channel_name
            )
        logger.info(f"Store notification WebSocket disconnected for store {self.store_id}")

    async def new_order(self, event):
        """Send new order notification to store owner"""
        order_data = event['order']
        
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order': order_data
        }))

    async def low_stock_alert(self, event):
        """Send low stock alert to store owner"""
        product_data = event['product']
        
        await self.send(text_data=json.dumps({
            'type': 'low_stock_alert',
            'product': product_data
        }))

    async def review_notification(self, event):
        """Send new review notification to store owner"""
        review_data = event['review']
        
        await self.send(text_data=json.dumps({
            'type': 'new_review',
            'review': review_data
        }))

    @database_sync_to_async
    def check_store_access(self, user, store_id):
        """Check if user owns the store"""
        try:
            from apps.stores.models import Store
            store = Store.objects.get(id=store_id)
            return store.owner == user
            
        except Store.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking store access: {str(e)}")
            return False