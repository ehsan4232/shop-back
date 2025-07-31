import requests
import json
from django.conf import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS service for sending OTP codes
    Supports Iranian SMS providers: Kavenegar, SmsIr
    """
    
    def __init__(self):
        self.provider = getattr(settings, 'SMS_PROVIDER', 'kavenegar')
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sender = getattr(settings, 'SMS_SENDER', '')
        
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using configured provider
        """
        if not self.api_key:
            logger.error("SMS API key not configured")
            return {'success': False, 'error': 'SMS service not configured'}
            
        if self.provider == 'kavenegar':
            return self._send_kavenegar(phone_number, message)
        elif self.provider == 'smsir':
            return self._send_smsir(phone_number, message)
        else:
            logger.error(f"Unsupported SMS provider: {self.provider}")
            return {'success': False, 'error': 'Unsupported SMS provider'}
    
    def _send_kavenegar(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using Kavenegar API
        """
        try:
            url = f"https://api.kavenegar.com/v1/{self.api_key}/sms/send.json"
            
            data = {
                'receptor': phone_number,
                'sender': self.sender,
                'message': message
            }
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('return', {}).get('status') == 200:
                    logger.info(f"SMS sent successfully to {phone_number}")
                    return {
                        'success': True,
                        'message_id': result.get('entries', [{}])[0].get('messageid'),
                        'provider': 'kavenegar'
                    }
                else:
                    error_msg = result.get('return', {}).get('message', 'Unknown error')
                    logger.error(f"Kavenegar API error: {error_msg}")
                    return {'success': False, 'error': error_msg}
            else:
                logger.error(f"Kavenegar HTTP error: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.Timeout:
            logger.error("Kavenegar request timeout")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Kavenegar request error: {str(e)}")
            return {'success': False, 'error': 'Network error'}
        except Exception as e:
            logger.error(f"Kavenegar unexpected error: {str(e)}")
            return {'success': False, 'error': 'Unexpected error'}
    
    def _send_smsir(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using SmsIr API
        """
        try:
            # Get token first
            token_url = "https://RestfulSms.com/api/Token"
            token_data = {
                'UserApiKey': self.api_key,
                'SecretKey': getattr(settings, 'SMS_SECRET_KEY', '')
            }
            
            token_response = requests.post(token_url, json=token_data, timeout=30)
            
            if token_response.status_code != 201:
                return {'success': False, 'error': 'Failed to get SMS token'}
            
            token = token_response.json().get('TokenKey')
            
            # Send SMS
            sms_url = "https://RestfulSms.com/api/MessageSend"
            headers = {
                'Content-Type': 'application/json',
                'x-sms-ir-secure-token': token
            }
            
            sms_data = {
                'Messages': [message],
                'MobileNumbers': [phone_number],
                'LineNumber': self.sender,
                'SendDateTime': '',
                'CanContinueInCaseOfError': True
            }
            
            response = requests.post(sms_url, json=sms_data, headers=headers, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"SMS sent successfully to {phone_number}")
                return {
                    'success': True,
                    'message_id': result.get('MessageSendResponseData', {}).get('Ids', [])[0] if result.get('MessageSendResponseData', {}).get('Ids') else None,
                    'provider': 'smsir'
                }
            else:
                logger.error(f"SmsIr HTTP error: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.Timeout:
            logger.error("SmsIr request timeout")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"SmsIr request error: {str(e)}")
            return {'success': False, 'error': 'Network error'}
        except Exception as e:
            logger.error(f"SmsIr unexpected error: {str(e)}")
            return {'success': False, 'error': 'Unexpected error'}
    
    def send_otp(self, phone_number: str, code: str) -> Dict[str, Any]:
        """
        Send OTP code with standard template
        """
        message = f"کد تایید مال: {code}\nاین کد تا ۲ دقیقه معتبر است."
        return self.send_sms(phone_number, message)
    
    def send_welcome(self, phone_number: str, first_name: str) -> Dict[str, Any]:
        """
        Send welcome message for new users
        """
        message = f"سلام {first_name}!\nخوش آمدید به فروشگاه‌ساز مال. حساب شما با موفقیت ایجاد شد."
        return self.send_sms(phone_number, message)
    
    def send_order_confirmation(self, phone_number: str, order_id: str) -> Dict[str, Any]:
        """
        Send order confirmation
        """
        message = f"سفارش شما با شماره {order_id} ثبت شد. از خرید شما متشکریم."
        return self.send_sms(phone_number, message)


# Utility function for easy access
def send_otp_sms(phone_number: str, code: str) -> Dict[str, Any]:
    """
    Quick function to send OTP SMS
    """
    service = SMSService()
    return service.send_otp(phone_number, code)