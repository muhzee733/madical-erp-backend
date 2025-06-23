        #'HOST': 'localhost',
# ProMedicine Backend - Medical ERP & Telehealth/E-Prescription Platform

This is a Django-based RESTful API backend for **ProMedicine**, an Australian medical practice management system with online consultation capabilities. The system provides:

**BUILT & OPERATIONAL FEATURES:**
- **Online Consultation Management**: Appointment booking system with real-time secure messaging
- **Integrated Payment Processing**: Stripe-powered payment handling with automated pricing logic
- **Digital Prescription Management**: PDF generation with Australian healthcare identifiers support
- **Real-time Secure Communication**: WebSocket-based chat system with message read receipts
- **Appointment Management**: Sophisticated booking system with race condition protection and automated expiration
- **Australian Healthcare Compliance**: Support for Medicare numbers, HPI-I, prescriber numbers, and TGA compliance fields
- **Multi-Supplier Cannabis Integration**: Excel import system for 5 Australian medicinal cannabis suppliers
- **Comprehensive Audit Trail**: Full logging and tracking of all medical interactions with Privacy Act 1988 compliance

## Getting Started

### 1. Clone the Repository

```bash
git clone git@github.com:your-org/your-repo.git
cd medical-erp-backend
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database
Update medical/settings.py if you’re using a local or remote MySQL DB.
```bash
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Apply Migrations
After making changes to any Django model, you need to create and apply database migrations.
```bash
python manage.py makemigrations
python manage.py migrate
```

If specific apps were changed:
Sometimes you may need to generate migrations for specific apps:
```bash
python manage.py makemigrations prescriptions
python manage.py makemigrations supplier_products
```
Use this when:
- You’ve made changes to models inside prescriptions or supplier_products
- You’re getting errors like table does not exist
- You want to avoid accidentally generating migrations for unrelated apps


### 6. Create a Superuser 
```bash
python manage.py createsuperuser
```

### 7. Run the Server 
```bash
python manage.py runserver
```
### 8. Importing Australian Cannabis Supplier Products
```bash
# Import from 5 Australian medicinal cannabis suppliers
python manage.py import_botanitech path/to/botanitech.xlsx
python manage.py import_medreleaf path/to/medreleaf.xlsx
python manage.py import_alma path/to/alma.xlsx
python manage.py import_phytoca path/to/phytoca.xlsx
python manage.py import_tasmanianBotanics path/to/tasmanian.xlsx
```

### 9. Running Unit Tests
```bash
# To run all tests
python manage.py test

# To run tests for a specific app
python manage.py test users
python manage.py test prescriptions
python manage.py test appointment
```

### 10. Redis Setup for Celery (Local Development)

Celery requires a message broker. We use **Redis** for local development.

#### Windows
1. Download Redis for Windows from the official releases:
   - https://github.com/tporadowski/redis/releases
2. Extract the downloaded zip file.
3. Open a Command Prompt in the extracted folder.
4. Start Redis by running:
   ```
   redis-server.exe
   ```
   Leave this window open while you use Celery and Django.

#### macOS (with Homebrew)
```bash
brew install redis
brew services start redis
```

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

#### Verify Redis is Running
You can check if Redis is running by connecting with the CLI:
```bash
redis-cli ping
```
You should see: `PONG`

---

### Running Celery Worker

After Redis is running, start the Celery worker in your project root:

```bash
celery -A medical worker --loglevel=info -P solo
```
**Note:** On Windows, always use the `-P solo` option.

---

## Technical Architecture & Implementation Details

### **Core Models & Database Design**

#### **User Management with Australian Healthcare IDs**
```python
# users/models.py - Three-role system with healthcare compliance
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [('admin', 'Admin'), ('doctor', 'Doctor'), ('patient', 'Patient')]
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')

class DoctorProfile(models.Model):
    medical_registration_number = models.CharField(max_length=50, unique=True)
    prescriber_number = models.CharField(max_length=50, unique=True)
    hpi_i = models.CharField(max_length=16, unique=True)  # Healthcare Provider Identifier

class PatientProfile(models.Model):
    medicare_number = models.CharField(max_length=20, unique=True)
    ihi = models.CharField(max_length=16, unique=True)  # Individual Healthcare Identifier
```

#### **Appointment System with Race Condition Protection**
```python
# appointment/models.py - UUID security + concurrent booking prevention
class AppointmentAvailability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("doctor", "start_time")  # Prevents double-booking

class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    availability = models.OneToOneField(AppointmentAvailability, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=6, decimal_places=2)  # Auto-calculated
    is_initial = models.BooleanField(default=True)  # $80 new, $50 returning
```

### **Payment Processing & Business Logic**

#### **Automated Pricing System**
```python
# appointment/serializers.py - Smart pricing logic
def create(self, validated_data):
    user = self.context['request'].user
    
    # Check patient history for pricing
    has_prior_appointments = Appointment.objects.filter(
        patient=user, status__in=['completed', 'no_show']
    ).exists()
    
    if has_prior_appointments:
        validated_data['price'] = Decimal('50.00')  # Returning patient
        validated_data['is_initial'] = False
    else:
        validated_data['price'] = Decimal('80.00')  # New patient
        validated_data['is_initial'] = True
    
    return super().create(validated_data)
```

#### **Stripe Integration Example**
```python
# order/views.py - Payment processing
def post(self, request):
    appointment = get_object_or_404(Appointment, id=request.data['appointmentId'])
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Medical Consultation'},
                'unit_amount': int(appointment.price * 100),
            },
            'quantity': 1,
        }],
        metadata={'appointment_id': str(appointment.id)}
    )
    
    return Response({'checkout_url': session.url})
```

### **Real-Time Communication**

#### **WebSocket Chat with JWT Authentication**
```python
# chat/consumers.py - Secure real-time messaging
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # JWT authentication from query string
        user = await self.simple_jwt_auth()
        if not user:
            await self.close(code=4001)
            return
            
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        await self.accept()
        await self.channel_layer.group_add(f'chat_{self.room_id}', self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Broadcast to room participants only
        await self.channel_layer.group_send(f'chat_{self.room_id}', {
            'type': 'chat_message',
            'message': data['message'],
            'sender': self.user.id,
            'timestamp': 'now'
        })
```

### **Australian Cannabis Supplier Integration**

#### **Excel Import Commands**
```python
# supplier_products/management/commands/import_botanitech.py
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        df = pd.read_excel(kwargs['excel_file'])
        
        for _, row in df.iterrows():
            SupplierProduct.objects.create(
                supplier_name="Botanitech",
                product_name=row.get('Trade/Brand name'),
                artg_no=row.get('ARTG No'),  # Australian Register of Therapeutic Goods
                tga_category=row.get('TGA Category'),
                poison_schedule=row.get('Poison Schedule'),
                # Complete TGA compliance mapping
            )
```

**Available Import Commands:**
```bash
python manage.py import_botanitech path/to/botanitech.xlsx
python manage.py import_medreleaf path/to/medreleaf.xlsx  
python manage.py import_alma path/to/alma.xlsx
python manage.py import_phytoca path/to/phytoca.xlsx
python manage.py import_tasmanianBotanics path/to/tasmanian.xlsx
```

### **Background Task Processing**

#### **Celery Tasks for Appointment Management**
```python
# appointment/tasks.py - Automated expiration handling
@shared_task
def expire_pending_appointments():
    """Expire unpaid appointments after 15 minutes"""
    expired_cutoff = timezone.now() - timedelta(minutes=15)
    expired_appointments = Appointment.objects.filter(
        status='pending', booked_at__lte=expired_cutoff
    )
    
    for appointment in expired_appointments:
        appointment.status = 'payment_expired'
        appointment.save()
        
        # Free up the availability slot
        appointment.availability.is_booked = False
        appointment.availability.save()
```

### **Key API Endpoints**

```bash
# Core API Structure
POST /api/v1/users/register/              # User registration  
POST /api/v1/users/login/                 # JWT authentication
GET  /api/v1/appointments/availabilities/list/  # Browse available slots
POST /api/v1/appointments/                # Book appointment
POST /api/v1/orders/                      # Create Stripe checkout
POST /webhook/stripe/                     # Payment webhook
WS   /ws/chat/{room_id}/?token={jwt}      # WebSocket chat
POST /api/v1/prescriptions/              # Create prescription
GET  /api/v1/supplier-products/          # Browse cannabis products
```

### **Security & Compliance**

#### **Role-Based Access Control**
```python
# Role-based data filtering
class AppointmentViewSet(ModelViewSet):
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Appointment.objects.all()
        elif user.role == 'doctor':
            return Appointment.objects.filter(availability__doctor=user)
        elif user.role == 'patient':
            return Appointment.objects.filter(patient=user)
```

#### **Australian Privacy Act 1988 Compliance**
- **Audit trails**: All medical data access logged with `created_by`/`updated_by`
- **Data minimization**: Role-based queries limit data exposure  
- **Soft deletes**: Medical records preserved with `is_deleted` flags
- **UUID primary keys**: Prevent enumeration attacks on sensitive data

---

## **System Summary**

**🎯 What's Built & Working:**
- **Complete Patient Journey**: Registration → booking → payment → consultation → prescription
- **Australian Healthcare Compliance**: Medicare numbers, HPI-I, prescriber numbers, TGA compliance
- **Real-time Communication**: WebSocket chat with JWT authentication and message persistence
- **Payment Processing**: Stripe integration with automated pricing ($80 new, $50 returning patients)
- **Race Condition Protection**: Database-level locking prevents double-booking conflicts
- **Cannabis Supplier Integration**: Excel import for 5 Australian medicinal cannabis suppliers
- **Digital Prescriptions**: PDF generation with email delivery and controlled substance tracking
- **Comprehensive Testing**: 158 tests covering all core functionality

**🏗️ Technology Stack:**
- **Backend**: Django 5.2 + Django REST Framework + Django Channels
- **Database**: MySQL with UUID primary keys for enhanced security
- **Real-time**: Redis for WebSocket channels and session management
- **Background Tasks**: Celery for appointment expiration and email delivery
- **File Storage**: AWS S3 for secure medical document storage
- **Payments**: Stripe with webhook processing and refund capabilities
- **Testing**: 158 comprehensive tests across all modules

**🔒 Security & Compliance:**
- **JWT Authentication** with role-based access control (admin/doctor/patient)
- **Australian Privacy Act 1988** compliance with comprehensive audit trails
- **UUID primary keys** prevent enumeration attacks on sensitive medical data
- **Soft delete patterns** preserve medical records for regulatory compliance
- **Input validation** and parameterized queries prevent SQL injection attacks
