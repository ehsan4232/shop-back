import requests
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone
from .models import Notification, NotificationTemplate, SMSLog, EmailLog

logger = logging.getLogger(__name__)

class CommunicationError(Exception):
    """Custom exception for communication errors"""
    pass

class SMSService:
    """
    SMS service using Kavenegar API (popular Iranian SMS provider)
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')
        self.base_url = 'https://api.kavenegar.com/v1'
        self.sender = getattr(settings, 'SMS_SENDER_NUMBER', '10008663')
    
    def send_sms(self, phone: str, message: str, template_name: str = None) -> Dict:
        """
        Send SMS message
        """
        try:
            if not self.api_key:
                raise CommunicationError("SMS API key not configured")
            
            # Clean phone number
            phone = self._clean_phone_number(phone)
            
            if template_name:
                # Use template-based SMS
                response = self._send_template_sms(phone, template_name, message)
            else:
                # Send simple SMS
                response = self._send_simple_sms(phone, message)
            
            # Log SMS
            SMSLog.objects.create(
                phone=phone,
                message=message,
                template_name=template_name,
                status='sent' if response.get('success') else 'failed',
                provider_response=response,
                cost=response.get('cost', 0)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"SMS sending error: {e}")
            
            # Log failed SMS
            SMSLog.objects.create(
                phone=phone,
                message=message,
                template_name=template_name,
                status='failed',
                error_message=str(e)
            )
            
            raise CommunicationError(f"Failed to send SMS: {e}")
    
    def _send_simple_sms(self, phone: str, message: str) -> Dict:
        """Send simple SMS"""
        url = f"{self.base_url}/{self.api_key}/sms/send.json"
        
        data = {
            'receptor': phone,
            'sender': self.sender,
            'message': message
        }
        
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result['return']['status'] == 200:
            return {
                'success': True,
                'message_id': result['entries'][0]['messageid'],
                'cost': result['entries'][0]['cost']
            }
        else:
            return {
                'success': False,
                'error': result['return']['message']
            }
    
    def _send_template_sms(self, phone: str, template: str, tokens: str) -> Dict:
        """Send template-based SMS"""
        url = f"{self.base_url}/{self.api_key}/verify/lookup.json"
        
        data = {
            'receptor': phone,
            'template': template,
            'token': tokens,
            'type': 'sms'
        }
        
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result['return']['status'] == 200:
            return {
                'success': True,
                'message_id': result['entries'][0]['messageid']
            }
        else:
            return {
                'success': False,
                'error': result['return']['message']
            }
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and validate phone number"""
        # Remove non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Convert to international format
        if phone.startswith('0'):
            phone = '98' + phone[1:]
        elif not phone.startswith('98'):
            phone = '98' + phone
        
        return phone
    
    def send_otp(self, phone: str, otp_code: str) -> Dict:
        """Send OTP code"""
        template_name = 'otp-verification'
        return self.send_sms(phone, otp_code, template_name)
    
    def send_order_notification(self, phone: str, order_number: str, status: str) -> Dict:
        """Send order status notification"""
        status_messages = {
            'paid': f'سفارش {order_number} با موفقیت پرداخت شد.',
            'processing': f'سفارش {order_number} در حال پردازش است.',
            'shipped': f'سفارش {order_number} ارسال شد.',
            'delivered': f'سفارش {order_number} تحویل داده شد.',
            'cancelled': f'سفارش {order_number} لغو شد.'
        }
        
        message = status_messages.get(status, f'وضعیت سفارش {order_number} تغییر کرد.')
        return self.send_sms(phone, message)

class EmailService:
    """
    Email service for sending notifications
    """
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mall.ir')
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        message: str = None,
        html_message: str = None,
        template_name: str = None,
        context: Dict = None
    ) -> Dict:
        """
        Send email
        """
        try:
            if template_name and context:
                # Render template
                html_message = render_to_string(f'emails/{template_name}.html', context)
                message = render_to_string(f'emails/{template_name}.txt', context)
            
            # Send email
            result = send_mail(
                subject=subject,
                message=message or '',
                from_email=self.from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Log email
            EmailLog.objects.create(
                to_email=to_email,
                subject=subject,
                template_name=template_name,
                status='sent' if result else 'failed'
            )
            
            return {
                'success': bool(result),
                'message': 'Email sent successfully' if result else 'Failed to send email'
            }
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            
            # Log failed email
            EmailLog.objects.create(
                to_email=to_email,
                subject=subject,
                template_name=template_name,
                status='failed',
                error_message=str(e)
            )
            
            raise CommunicationError(f"Failed to send email: {e}")
    
    def send_order_confirmation(self, order) -> Dict:
        """Send order confirmation email"""
        if not order.customer_email:
            return {'success': False, 'message': 'No email address'}
        
        context = {
            'order': order,
            'store': order.store,
            'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
            'items': order.items.all()
        }
        
        return self.send_email(
            to_email=order.customer_email,
            subject=f'تأیید سفارش {order.order_number}',
            template_name='order_confirmation',
            context=context
        )
    
    def send_order_status_update(self, order, old_status: str, new_status: str) -> Dict:
        """Send order status update email"""
        if not order.customer_email:
            return {'success': False, 'message': 'No email address'}
        
        context = {
            'order': order,
            'store': order.store,
            'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
            'old_status': old_status,
            'new_status': new_status,
            'status_display': order.get_status_display()
        }
        
        return self.send_email(
            to_email=order.customer_email,
            subject=f'به‌روزرسانی وضعیت سفارش {order.order_number}',
            template_name='order_status_update',
            context=context
        )

class NotificationService:
    """
    Main notification service
    """
    
    def __init__(self):
        self.sms_service = SMSService()
        self.email_service = EmailService()
    
    def send_order_notifications(self, order, event_type: str) -> Dict:
        """
        Send order-related notifications
        """
        results = {
            'sms': {'success': False},
            'email': {'success': False},
            'push': {'success': False}
        }
        
        try:
            # Send SMS notification
            if order.customer_phone:
                try:
                    results['sms'] = self.sms_service.send_order_notification(
                        order.customer_phone,
                        order.order_number,
                        order.status
                    )
                except Exception as e:
                    logger.error(f"SMS notification error: {e}")
                    results['sms'] = {'success': False, 'error': str(e)}
            
            # Send email notification
            if order.customer_email:
                try:
                    if event_type == 'created':
                        results['email'] = self.email_service.send_order_confirmation(order)
                    elif event_type == 'status_changed':
                        # Get old status from history
                        history = order.status_history.order_by('-created_at').first()
                        old_status = history.old_status if history else 'pending'
                        results['email'] = self.email_service.send_order_status_update(
                            order, old_status, order.status
                        )
                except Exception as e:
                    logger.error(f"Email notification error: {e}")
                    results['email'] = {'success': False, 'error': str(e)}
            
            # Create in-app notification
            if order.customer:
                try:
                    self.create_in_app_notification(
                        user=order.customer,
                        title=f'سفارش {order.order_number}',
                        message=self._get_order_notification_message(order, event_type),
                        notification_type='order_status',
                        action_url=f'/orders/{order.id}/'
                    )
                    results['push'] = {'success': True}
                except Exception as e:
                    logger.error(f"In-app notification error: {e}")
                    results['push'] = {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Notification service error: {e}")
        
        return results
    
    def send_otp_notification(self, phone: str, otp_code: str) -> Dict:
        """Send OTP code via SMS"""
        try:
            return self.sms_service.send_otp(phone, otp_code)
        except Exception as e:
            logger.error(f"OTP notification error: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_welcome_message(self, user) -> Dict:
        """Send welcome message to new users"""
        results = {
            'sms': {'success': False},
            'email': {'success': False}
        }
        
        # Send welcome SMS
        if user.phone:
            try:
                welcome_message = f'به پلتفرم مال خوش آمدید {user.first_name}! فروشگاه آنلاین خود را همین امروز بسازید.'
                results['sms'] = self.sms_service.send_sms(user.phone, welcome_message)
            except Exception as e:
                logger.error(f"Welcome SMS error: {e}")
        
        # Send welcome email
        if user.email:
            try:
                context = {
                    'user': user,
                    'platform_url': settings.SITE_URL
                }
                results['email'] = self.email_service.send_email(
                    to_email=user.email,
                    subject='به پلتفرم مال خوش آمدید',
                    template_name='welcome',
                    context=context
                )
            except Exception as e:
                logger.error(f"Welcome email error: {e}")
        
        return results
    
    def create_in_app_notification(
        self, 
        user, 
        title: str, 
        message: str,
        notification_type: str = 'system',
        action_url: str = None,
        data: Dict = None
    ) -> 'UserNotification':
        """Create in-app notification"""
        from apps.accounts.models import UserNotification
        
        return UserNotification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            data=data or {}
        )
    
    def send_low_stock_alert(self, store, products: List) -> Dict:
        """Send low stock alert to store owner"""
        try:
            # Prepare product list
            product_list = '\n'.join([
                f"- {p.name_fa}: {p.stock_quantity} عدد"
                for p in products[:10]  # Limit to 10 products
            ])
            
            if len(products) > 10:
                product_list += f"\n... و {len(products) - 10} محصول دیگر"
            
            # Send SMS to store owner
            sms_message = f'هشدار موجودی کم!\n{len(products)} محصول موجودی کم دارند.\n{product_list}'
            
            sms_result = self.sms_service.send_sms(
                store.owner.phone,
                sms_message
            )
            
            # Create in-app notification
            self.create_in_app_notification(
                user=store.owner,
                title='هشدار موجودی کم',
                message=f'{len(products)} محصول موجودی کم دارند',
                notification_type='system',
                action_url='/admin/products/?low_stock=true',
                data={'product_count': len(products)}
            )
            
            return {
                'success': True,
                'sms_result': sms_result,
                'products_count': len(products)
            }
            
        except Exception as e:
            logger.error(f"Low stock alert error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_order_notification_message(self, order, event_type: str) -> str:
        """Get notification message for order events"""
        messages = {
            'created': f'سفارش شما با شماره {order.order_number} ثبت شد.',
            'status_changed': f'وضعیت سفارش {order.order_number} به {order.get_status_display()} تغییر کرد.',
            'payment_completed': f'پرداخت سفارش {order.order_number} با موفقیت انجام شد.',
            'shipped': f'سفارش {order.order_number} ارسال شد. کد رهگیری: {order.tracking_number}',
            'delivered': f'سفارش {order.order_number} تحویل داده شد.',
        }
        
        return messages.get(event_type, f'به‌روزرسانی سفارش {order.order_number}')
    
    def get_notification_statistics(self, store=None, days: int = 30) -> Dict:
        """Get notification statistics"""
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        # SMS statistics
        sms_logs = SMSLog.objects.filter(created_at__gte=start_date)
        if store:
            # Filter by store (you'd need to add store field to SMSLog)
            pass
        
        sms_stats = {
            'total_sent': sms_logs.filter(status='sent').count(),
            'total_failed': sms_logs.filter(status='failed').count(),
            'total_cost': sum(log.cost for log in sms_logs.filter(status='sent')),
        }
        
        # Email statistics
        email_logs = EmailLog.objects.filter(created_at__gte=start_date)
        email_stats = {
            'total_sent': email_logs.filter(status='sent').count(),
            'total_failed': email_logs.filter(status='failed').count(),
        }
        
        return {
            'sms': sms_stats,
            'email': email_stats,
            'period_days': days
        }
