# ProMedicine Backend (e-Prescribing Platform)

This is a Django-based RESTful API backend for **ProMedicine**, an e-Prescribing platform. It supports:

- User registration and authentication
- Prescription management
- Drug registry
- Supplier product import via Excel
- PDF generation for prescriptions

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
### 8. Importing Excel Supplier Products/data
```bash
python manage.py import_botanitech path/to/file.xlsx
python manage.py import_medreleaf path/to/file.xlsx
```





## User Endpoints

### Dashboard Endpoints

| **Role**   | **Endpoint**                             | **Description**                            |
|------------|------------------------------------------|--------------------------------------------|
| Admin      | `/api/v1/users/dashboard/admin/`         | Access control panel and user management, View, update, and delete all user accounts  |
| Doctor     | `/api/v1/users/dashboard/doctor/`        | Access dashboard for doctors, Create and manage prescriptions                   |
| Patient    | `/api/v1/users/dashboard/patient/`       | Access dashboard for patients, View their prescriptions and profile                  |

---

### Admin-Level User Management API

> These endpoints require an authenticated user with the **admin** role.

| **Action**         | **Endpoint**                                | **Method**         |
|--------------------|---------------------------------------------|--------------------|
| List all users     | `/api/v1/users/admin/users/`                | `GET`              |
| Retrieve a user    | `/api/v1/users/admin/users/<id>/`           | `GET`              |
| Update a user      | `/api/v1/users/admin/users/<id>/`           | `PUT` / `PATCH`    |
| Delete a user      | `/api/v1/users/admin/users/<id>/`           | `DELETE`           |



| Endpoint                    | Method | Description                  | Auth Required | Sample Body                                                                                         |
|----------------------------|--------|------------------------------|----------------|------------------------------------------------------------------------------------------------------|
| `/api/v1/users/register/`  | POST   | Register a new user          | ❌              | `{ "first_name": "Sam", "last_name": "Smith", "email": "sam@example.com", "password": "123456", "phone_number": "0412345678", "role": "doctor" }` |
| `/api/v1/users/login/`     | POST   | Log in and receive token     | ❌              | `{ "email": "sam@example.com", "password": "123456" }`                                               |


### Drug Endpoints

| Endpoint         | Method     | Description             | Auth Required     | Sample Body                                                                                           |
|------------------|------------|-------------------------|--------------------|--------------------------------------------------------------------------------------------------------|
| `/api/v1/drugs/` | GET / POST | List all or create drug | ✅ Admin, Doctor    | `{ "name": "Panadol", "molecule": "Paracetamol", "strength": "500mg", "form": "Tablet", "category": "Analgesic", "is_schedule_8": false, "notes": "Take after food" }` |


### Prescription Endpoints

| Endpoint                                  | Method | Description                        | Auth Required            | Notes                                                            |
|-------------------------------------------|--------|------------------------------------|---------------------------|------------------------------------------------------------------|
| `/api/v1/prescriptions/`                  | POST   | Create a prescription              | ✅ Doctor only             |                                                                  |
| `/api/v1/prescriptions/list/`             | GET    | List prescriptions                 | ✅ Admin/Doctor/Patient    | Optional query: `?patient_name=`                                |
| `/api/v1/prescriptions/list/?search=`     | GET    | Search by doctor/patient name      | ✅ Admin/Doctor/Patient    | Example: `/api/v1/prescriptions/list/?search=smith`             |
| `/api/v1/prescriptions/pdf/<id>/`         | GET    | Generate PDF for a prescription    | ✅ Doctor (creator) / Admin| Replace `<id>` with prescription ID                              |

### Supplier Product Endpoints

| Endpoint                       | Method | Description                      | Auth Required | Notes                                          |
|--------------------------------|--------|----------------------------------|----------------|------------------------------------------------|
| `/api/v1/supplier-products/`   | GET    | List imported supplier products | ✅              | Optional query param: `?supplier_name=`        |


###  How to Test
You can test the API using [Postman](https://postman.com), [Insomnia](https://insomnia.rest), or `curl`.
Use /api/v1/users/login/ to obtain your access token:
### Register a User 
POST /api/v1/users/register/
```bash
{
  "first_name": "Sam",
  "last_name": "Smith",
  "email": "sam@example.com",
  "password": "123456",
  "phone_number": "0412345678",
  "role": "doctor"
}
```
### Login and Get JWT Token
POST /api/v1/users/register/
Authorization: Bearer <your_token>
```bash
{
  "email": "sam@example.com",
  "password": "123456"
}
```

### Create a Prescription
POST /api/v1/prescriptions/
Headers: 
Authorization: Bearer <your_token>
Content-Type: application/json

Authorization: Bearer <your_token>
```bash
{
  "patient": 1,
  "prescribed_drugs": [
    {
      "drug": 3,
      "dosage_instructions": "Take 1 tablet every 6 hours after meals"
    }
  ],
  "notes": "Patient has mild symptoms",
  "clinic_name": "Wellness Clinic"
}
```
### List supplier products
GET /api/v1/supplier-products/

Expected output in JSON
```bash
[
  {
    "id": 1,
    "product_name": "CBD Oil 50mg",
    "supplier": "MedReleaf",
    "form": "Oil",
    "strength": "50mg/mL",
    "category": "Cannabinoid"
  },
  ...
]
```
