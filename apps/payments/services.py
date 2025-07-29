import requests
import json
import hashlib
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import Payment, PaymentMethod

logger = logging.getLogger(__name__)

class PaymentError(Exception):
    """Custom exception for payment errors"""
    pass

class ZarinPalGateway:
    """
    ZarinPal payment gateway integration
    """
    
    def __init__(self):
        self.merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', '')
        self.sandbox = getattr(settings, 'ZARINPAL_SANDBOX', True)
        self.base_url = 'https://sandbox.zarinpal.com' if self.sandbox else 'https://zarinpal.com'
    
    def create_payment(self, amount: int, description: str, callback_url: str, metadata: Dict = None) -> Tuple[str, str]:
        """
        Create payment request
        Returns: (authority, payment_url)
        """
        try:
            data = {
                'MerchantID': self.merchant_id,
                'Amount': amount,
                'Description': description,
                'CallbackURL': callback_url,
            }
            
            if metadata:
                data['Metadata'] = metadata
            
            response = requests.post(
                f'{self.base_url}/pg/rest/WebGate/PaymentRequest.json',
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result['Status'] == 100:
                authority = result['Authority']
                payment_url = f'{self.base_url}/pg/StartPay/{authority}'
                return authority, payment_url
            else:
                raise PaymentError(f"ZarinPal error: {result.get('Status', 'Unknown error')}")
                
        except requests.RequestException as e:
            logger.error(f"ZarinPal request error: {e}")
            raise PaymentError(f"Payment gateway connection failed: {e}")
        except Exception as e:
            logger.error(f"ZarinPal unexpected error: {e}")
            raise PaymentError(f"Unexpected payment error: {e}")
    
    def verify_payment(self, authority: str, amount: int) -> Dict:
        """
        Verify payment
        """
        try:
            data = {
                'MerchantID': self.merchant_id,
                'Authority': authority,
                'Amount': amount,
            }
            
            response = requests.post(
                f'{self.base_url}/pg/rest/WebGate/PaymentVerification.json',
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': result['Status'] == 100,
                'ref_id': result.get('RefID'),
                'status': result.get('Status'),
                'message': self._get_status_message(result.get('Status'))
            }
            
        except requests.RequestException as e:
            logger.error(f"ZarinPal verification error: {e}")
            raise PaymentError(f"Payment verification failed: {e}")
    
    def _get_status_message(self, status: int) -> str:
        """Get human-readable status message"""
        messages = {
            100: 'پرداخت موفق',
            101: 'پرداخت قبلاً تأیید شده',
            -9: 'خطای اعتبارسنجی',
            -10: 'ترمینال معتبر نیست',
            -11: 'مرچنت معتبر نیست',
            -12: 'تلاش‌های ناموفق',
            -15: 'ترمینال معلق',
            -16: 'سطح تأیید پایین',
            -30: 'اجازه دسترسی به متد مربوطه وجود ندارد',
            -31: 'حساب کاربری فروشنده معلق شده',
            -32: 'کد فروشنده اشتباه است',
            -33: 'مبلغ تراکنش از حد مجاز بیشتر است',
            -34: 'مبلغ تراکنش از حد مجاز کمتر است',
            -40: 'متد فراخوانی معتبر نیست',
            -41: 'ادرس آی‌پی معتبر نیست',
            -50: 'مبلغ تراکنش معتبر نیست',
            -51: 'تراکنش ناموفق',
            -52: 'خطای غیرمنتظره',
            -53: 'پرداخت قبلاً انجام شده',
            -54: 'تراکنش یافت نشد',
        }
        return messages.get(status, f'خطای ناشناخته: {status}')

class ParsianGateway:
    """
    Parsian Bank payment gateway integration
    """
    
    def __init__(self):
        self.pin = getattr(settings, 'PARSIAN_PIN', '')
        self.base_url = 'https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx'
    
    def create_payment(self, amount: int, order_id: str, callback_url: str) -> Tuple[str, str]:
        """
        Create payment request
        """
        try:
            # Convert amount to Rials (multiply by 10)
            amount_rials = amount * 10
            
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <SalePaymentRequest xmlns="https://pec.shaparak.ir/NewIPGServices/Sale/SaleService">
                        <requestData>
                            <LoginAccount>{self.pin}</LoginAccount>
                            <Amount>{amount_rials}</Amount>
                            <OrderId>{order_id}</OrderId>
                            <CallBackUrl>{callback_url}</CallBackUrl>
                        </requestData>
                    </SalePaymentRequest>
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://pec.shaparak.ir/NewIPGServices/Sale/SaleService/SalePaymentRequest'
            }
            
            response = requests.post(
                self.base_url,
                data=soap_body,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse SOAP response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Extract token and status
            token_element = root.find('.//{https://pec.shaparak.ir/NewIPGServices/Sale/SaleService}Token')
            status_element = root.find('.//{https://pec.shaparak.ir/NewIPGServices/Sale/SaleService}Status')
            
            if token_element is not None and status_element is not None:
                token = token_element.text
                status = int(status_element.text)
                
                if status == 0:  # Success
                    payment_url = f'https://pec.shaparak.ir/NewIPG/?Token={token}'
                    return token, payment_url
                else:
                    raise PaymentError(f"Parsian error: Status {status}")
            else:
                raise PaymentError("Invalid response from Parsian gateway")
                
        except requests.RequestException as e:
            logger.error(f"Parsian request error: {e}")
            raise PaymentError(f"Payment gateway connection failed: {e}")
        except Exception as e:
            logger.error(f"Parsian unexpected error: {e}")
            raise PaymentError(f"Unexpected payment error: {e}")
    
    def verify_payment(self, token: str, order_id: str) -> Dict:
        """
        Verify payment
        """
        try:
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <ConfirmPayment xmlns="https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService">
                        <requestData>
                            <LoginAccount>{self.pin}</LoginAccount>
                            <Token>{token}</Token>
                        </requestData>
                    </ConfirmPayment>
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService/ConfirmPayment'
            }
            
            confirm_url = 'https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx'
            response = requests.post(
                confirm_url,
                data=soap_body,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            status_element = root.find('.//{https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService}Status')
            rrn_element = root.find('.//{https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService}RRN')
            
            if status_element is not None:
                status = int(status_element.text)
                rrn = rrn_element.text if rrn_element is not None else None
                
                return {
                    'success': status == 0,
                    'ref_id': rrn,
                    'status': status,
                    'message': 'پرداخت موفق' if status == 0 else f'خطا: {status}'
                }
            else:
                raise PaymentError("Invalid verification response")
                
        except requests.RequestException as e:
            logger.error(f"Parsian verification error: {e}")
            raise PaymentError(f"Payment verification failed: {e}")

class PaymentService:
    """
    Main payment service that handles different gateways
    """
    
    def __init__(self):
        self.gateways = {
            'zarinpal': ZarinPalGateway(),
            'parsian': ParsianGateway(),
        }
    
    def create_payment(self, order, gateway_name: str = 'zarinpal') -> Payment:
        """
        Create a new payment
        """
        try:
            gateway = self.gateways.get(gateway_name)
            if not gateway:
                raise PaymentError(f"Unsupported gateway: {gateway_name}")
            
            # Get or create payment method
            payment_method, _ = PaymentMethod.objects.get_or_create(
                store=order.store,
                gateway=gateway_name,
                defaults={
                    'name': gateway_name.title(),
                    'is_active': True
                }
            )
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=order.total_amount,
                currency='IRR',
                status='pending'
            )
            
            # Create callback URL
            callback_url = self._build_callback_url(payment)
            
            # Create payment with gateway
            if gateway_name == 'zarinpal':
                authority, payment_url = gateway.create_payment(
                    amount=int(payment.amount),
                    description=f"پرداخت سفارش {order.order_number}",
                    callback_url=callback_url,
                    metadata={
                        'order_id': str(order.id),
                        'store_id': str(order.store.id)
                    }
                )
                payment.gateway_transaction_id = authority
                
            elif gateway_name == 'parsian':
                token, payment_url = gateway.create_payment(
                    amount=int(payment.amount),
                    order_id=str(order.id),
                    callback_url=callback_url
                )
                payment.gateway_transaction_id = token
            
            payment.gateway_payment_url = payment_url
            payment.save()
            
            return payment
            
        except PaymentError:
            raise
        except Exception as e:
            logger.error(f"Payment creation error: {e}")
            raise PaymentError(f"Failed to create payment: {e}")
    
    def verify_payment(self, payment: Payment) -> bool:
        """
        Verify a payment
        """
        try:
            gateway_name = payment.payment_method.gateway
            gateway = self.gateways.get(gateway_name)
            
            if not gateway:
                raise PaymentError(f"Unsupported gateway: {gateway_name}")
            
            # Verify with gateway
            result = gateway.verify_payment(
                payment.gateway_transaction_id,
                int(payment.amount)
            )
            
            # Update payment record
            payment.gateway_response = result
            payment.reference_number = result.get('ref_id')
            
            if result['success']:
                payment.status = 'completed'
                payment.paid_at = timezone.now()
                
                # Update order status
                payment.order.payment_status = 'paid'
                if payment.order.status == 'pending':
                    payment.order.status = 'paid'
                payment.order.save()
                
            else:
                payment.status = 'failed'
                payment.failure_reason = result.get('message', 'Unknown error')
            
            payment.save()
            
            return result['success']
            
        except PaymentError:
            raise
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            payment.status = 'failed'
            payment.failure_reason = str(e)
            payment.save()
            raise PaymentError(f"Failed to verify payment: {e}")
    
    def refund_payment(self, payment: Payment, amount: Optional[Decimal] = None) -> bool:
        """
        Refund a payment (partial or full)
        """
        try:
            if payment.status != 'completed':
                raise PaymentError("Cannot refund non-completed payment")
            
            refund_amount = amount or payment.amount
            
            if refund_amount > payment.amount:
                raise PaymentError("Refund amount cannot exceed payment amount")
            
            # For now, mark as refunded (actual refund implementation depends on gateway)
            # In production, you'd implement actual refund API calls
            
            payment.refunded_amount = refund_amount
            if refund_amount == payment.amount:
                payment.status = 'refunded'
            else:
                payment.status = 'partially_refunded'
            
            payment.refunded_at = timezone.now()
            payment.save()
            
            # Update order status
            if payment.status == 'refunded':
                payment.order.payment_status = 'refunded'
                payment.order.save()
            
            return True
            
        except PaymentError:
            raise
        except Exception as e:
            logger.error(f"Payment refund error: {e}")
            raise PaymentError(f"Failed to refund payment: {e}")
    
    def _build_callback_url(self, payment: Payment) -> str:
        """
        Build callback URL for payment gateway
        """
        from django.contrib.sites.models import Site
        
        site = Site.objects.get_current()
        return f"https://{site.domain}{reverse('payment_callback', kwargs={'payment_id': payment.id})}"
    
    def get_payment_methods(self, store) -> list:
        """
        Get available payment methods for store
        """
        return PaymentMethod.objects.filter(
            store=store,
            is_active=True
        ).order_by('display_order')
    
    def calculate_gateway_fee(self, amount: Decimal, gateway_name: str) -> Decimal:
        """
        Calculate gateway fee
        """
        fees = {
            'zarinpal': Decimal('0.015'),  # 1.5%
            'parsian': Decimal('0.02'),    # 2%
        }
        
        fee_rate = fees.get(gateway_name, Decimal('0.02'))
        return amount * fee_rate
    
    def get_payment_analytics(self, store, start_date=None, end_date=None) -> Dict:
        """
        Get payment analytics for store
        """
        from django.db.models import Sum, Count, Q
        from datetime import datetime, timedelta
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        payments = Payment.objects.filter(
            order__store=store,
            created_at__range=[start_date, end_date]
        )
        
        total_payments = payments.count()
        successful_payments = payments.filter(status='completed').count()
        total_amount = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Payment method breakdown
        method_stats = payments.values('payment_method__name').annotate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        # Daily breakdown
        daily_stats = payments.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            count=Count('id'),
            amount=Sum('amount')
        ).order_by('day')
        
        success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
        
        return {
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'success_rate': round(success_rate, 2),
            'total_amount': total_amount,
            'average_amount': total_amount / successful_payments if successful_payments > 0 else 0,
            'payment_methods': list(method_stats),
            'daily_stats': list(daily_stats),
        }

# Utility functions
def validate_payment_amount(amount: Decimal, currency: str = 'IRR') -> bool:
    """
    Validate payment amount according to gateway limits
    """
    if currency == 'IRR':
        # Minimum 1000 Tomans, Maximum 50,000,000 Tomans
        return 1000 <= amount <= 50000000
    return True

def format_amount_for_display(amount: Decimal) -> str:
    """
    Format amount for display
    """
    return f"{amount:,.0f} تومان"

def generate_order_description(order) -> str:
    """
    Generate payment description for order
    """
    item_count = order.items.count()
    store_name = order.store.name_fa or order.store.name
    
    if item_count == 1:
        item = order.items.first()
        return f"خرید {item.product_name} از {store_name}"
    else:
        return f"خرید {item_count} کالا از {store_name}"
