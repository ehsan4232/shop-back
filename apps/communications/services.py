from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class SMSService:
    """SMS service using Kavenegar API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')
        self.sender = getattr(settings, 'SMS_SENDER', '10008663')
        self.base_url = 'https://api.kavenegar.com/v1/{}/sms/send.json'
    
    def send_sms(self, phone_number, message, template=None):
        """Send SMS using Kavenegar API"""
        if not self.api_key:
            logger.error("Kavenegar API key not configured")
            return False, "SMS service not configured"
        
        try:
            url = self.base_url.format(self.api_key)
            
            data = {
                'receptor': phone_number,
                'sender': self.sender,
                'message': message
            }
            
            if template:
                data['template'] = template
            
            response = requests.post(url, data=data, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('return', {}).get('status') == 200:
                logger.info(f"SMS sent successfully to {phone_number}")
                return True, "SMS sent successfully"
            else:
                error_msg = response_data.get('return', {}).get('message', 'Unknown error')
                logger.error(f"SMS sending failed: {error_msg}")
                return False, error_msg
                
        except requests.RequestException as e:
            logger.error(f"SMS sending error: {e}")
            return False, "Network error occurred"
        except Exception as e:
            logger.error(f"Unexpected SMS error: {e}")
            return False, "Unexpected error occurred"
    
    def send_otp(self, phone_number, otp_code):
        """Send OTP code via SMS"""
        message = f"کد تأیید شما: {otp_code}\nمال - فروشگاه‌ساز"
        return self.send_sms(phone_number, message)
    
    def send_order_notification(self, phone_number, order_number, status):
        """Send order status notification"""
        status_messages = {
            'paid': 'پرداخت شده',
            'processing': 'در حال پردازش',
            'shipped': 'ارسال شده',
            'delivered': 'تحویل داده شده',
            'cancelled': 'لغو شده'
        }
        
        status_text = status_messages.get(status, status)
        message = f"وضعیت سفارش {order_number}: {status_text}\nمال - فروشگاه‌ساز"
        return self.send_sms(phone_number, message)
    
    def send_bulk_sms(self, phone_numbers, message):
        """Send bulk SMS to multiple recipients"""
        results = []
        for phone in phone_numbers:
            success, msg = self.send_sms(phone, message)
            results.append({
                'phone': phone,
                'success': success,
                'message': msg
            })
        return results

class EmailService:
    """Email service for notifications"""
    
    def send_email(self, to_email, subject, message, html_message=None):
        """Send email notification"""
        try:
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return False, str(e)
    
    def send_order_confirmation(self, order):
        """Send order confirmation email"""
        subject = f"تأیید سفارش {order.order_number}"
        message = f"""
        سلام {order.customer_first_name} {order.customer_last_name}،
        
        سفارش شما با شماره {order.order_number} با موفقیت ثبت شد.
        مبلغ کل: {order.total_amount:,} تومان
        
        با تشکر،
        {order.store.name_fa}
        """
        
        return self.send_email(order.customer_email, subject, message)

# Create service instances
sms_service = SMSService()
email_service = EmailService()
