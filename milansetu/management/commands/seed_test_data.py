"""
Management command: python manage.py seed_test_data

Creates 8 realistic test users with full profiles, ideal partner preferences,
and sent/received interests — enough to test all implemented features:
  - Profile Sharing, Edit Restriction, Swipe, Send Interest,
    Interest Notifications, Profile View Tracking, Recent Views, My Matches.

Safe to re-run: skips existing users by email.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from users.models import User, UserType, UserRole
from milansetu.models import ProfileDetails, IdealPartner, SentInterest


USERS_DATA = [
    {
        "email": "aditya@milansetu.test",
        "phone": "9100000001",
        "password": "Test@1234",
        "user_type": UserType.GOLD,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Aditya Sharma",
            "age": 29,
            "height_cm": 178,
            "religion": "Hindu",
            "mother_tongue": "Hindi",
            "marital_status": "Never Married",
            "father_occupation": "Retired Government Officer",
            "mother_occupation": "Homemaker",
            "siblings_count": 1,
            "siblings_details": "1 sister, married",
            "family_values": "Traditional",
            "industry": "Information Technology",
            "education": "B.Tech Computer Science, IIT Bombay",
            "current_designation": "Software Architect",
            "current_company": "TechCorp India Pvt Ltd",
            "annual_income_min": "1800000.00",
            "annual_income_max": "2200000.00",
            "income_unit": "INR",
            "date_of_birth": "1995-03-15",
            "time_of_birth": "07:30:00",
            "birth_place": "Mumbai",
            "zodiac_sign": "Pisces",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 24, "age_max": 28,
            "height_min_cm": 155, "height_max_cm": 170,
            "religion": "Hindu",
            "location": "Mumbai, Delhi, Pune",
            "mother_tongue": "Hindi",
            "marital_status": "Never Married",
            "education": "Graduation or above",
            "industry": "Any",
            "family_values": "Traditional",
        },
    },
    {
        "email": "ananya@milansetu.test",
        "phone": "9100000002",
        "password": "Test@1234",
        "user_type": UserType.SILVER,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Ananya Mehta",
            "age": 27,
            "height_cm": 163,
            "religion": "Hindu",
            "mother_tongue": "Hindi",
            "marital_status": "Never Married",
            "father_occupation": "Business Owner",
            "mother_occupation": "Teacher",
            "siblings_count": 0,
            "siblings_details": "Only child",
            "family_values": "Modern",
            "industry": "Legal",
            "education": "LLB, Delhi University",
            "current_designation": "Corporate Lawyer",
            "current_company": "Mehta & Associates",
            "annual_income_min": "1200000.00",
            "annual_income_max": "1600000.00",
            "income_unit": "INR",
            "date_of_birth": "1997-07-22",
            "time_of_birth": "10:15:00",
            "birth_place": "Delhi",
            "zodiac_sign": "Cancer",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 27, "age_max": 33,
            "height_min_cm": 170, "height_max_cm": 185,
            "religion": "Hindu",
            "location": "Delhi, Mumbai, Bangalore",
            "mother_tongue": "Hindi",
            "education": "Post Graduate or above",
            "family_values": "Modern",
        },
    },
    {
        "email": "ravi@milansetu.test",
        "phone": "9100000003",
        "password": "Test@1234",
        "user_type": UserType.BASIC,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Ravi Kumar",
            "age": 31,
            "height_cm": 172,
            "religion": "Hindu",
            "mother_tongue": "Telugu",
            "marital_status": "Never Married",
            "father_occupation": "Farmer",
            "mother_occupation": "Homemaker",
            "siblings_count": 2,
            "siblings_details": "2 brothers, both working",
            "family_values": "Traditional",
            "industry": "Education",
            "education": "M.Ed, Osmania University",
            "current_designation": "Senior Teacher",
            "current_company": "Kendriya Vidyalaya, Hyderabad",
            "annual_income_min": "600000.00",
            "annual_income_max": "800000.00",
            "income_unit": "INR",
            "date_of_birth": "1993-11-08",
            "time_of_birth": "06:00:00",
            "birth_place": "Hyderabad",
            "zodiac_sign": "Scorpio",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 24, "age_max": 29,
            "height_min_cm": 155, "height_max_cm": 168,
            "religion": "Hindu",
            "location": "Hyderabad, Telangana",
        },
    },
    {
        "email": "priya@milansetu.test",
        "phone": "9100000004",
        "password": "Test@1234",
        "user_type": UserType.BASIC,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Priya Iyer",
            "age": 26,
            "height_cm": 159,
            "religion": "Hindu",
            "mother_tongue": "Tamil",
            "marital_status": "Never Married",
            "father_occupation": "Doctor",
            "mother_occupation": "Doctor",
            "siblings_count": 1,
            "siblings_details": "1 brother, medical student",
            "family_values": "Traditional",
            "industry": "Healthcare",
            "education": "MBBS, AIIMS Chennai",
            "current_designation": "Junior Resident Doctor",
            "current_company": "Apollo Hospitals, Chennai",
            "annual_income_min": "800000.00",
            "annual_income_max": "1000000.00",
            "income_unit": "INR",
            "date_of_birth": "1998-04-12",
            "time_of_birth": "14:30:00",
            "birth_place": "Chennai",
            "zodiac_sign": "Aries",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 27, "age_max": 35,
            "height_min_cm": 168, "height_max_cm": 185,
            "religion": "Hindu",
            "location": "Chennai, Bangalore, Hyderabad",
        },
    },
    {
        "email": "sai@milansetu.test",
        "phone": "9100000005",
        "password": "Test@1234",
        "user_type": UserType.BASIC,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Sai Reddy",
            "age": 28,
            "height_cm": 174,
            "religion": "Hindu",
            "mother_tongue": "Telugu",
            "marital_status": "Never Married",
            "father_occupation": "Business Owner",
            "mother_occupation": "Homemaker",
            "siblings_count": 1,
            "siblings_details": "1 sister, married",
            "family_values": "Traditional",
            "industry": "Engineering",
            "education": "B.Tech Mechanical, JNTU",
            "current_designation": "Senior Engineer",
            "current_company": "Bharat Heavy Electricals Ltd",
            "annual_income_min": "700000.00",
            "annual_income_max": "900000.00",
            "income_unit": "INR",
            "date_of_birth": "1996-09-20",
            "time_of_birth": "08:45:00",
            "birth_place": "Guntur",
            "zodiac_sign": "Virgo",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 23, "age_max": 27,
            "height_min_cm": 155, "height_max_cm": 167,
            "religion": "Hindu",
            "location": "Guntur, Hyderabad, Vijayawada",
        },
    },
    {
        "email": "deepika@milansetu.test",
        "phone": "9100000006",
        "password": "Test@1234",
        "user_type": UserType.PLATINUM,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Deepika Nair",
            "age": 28,
            "height_cm": 165,
            "religion": "Hindu",
            "mother_tongue": "Malayalam",
            "marital_status": "Never Married",
            "father_occupation": "IAS Officer",
            "mother_occupation": "Professor",
            "siblings_count": 1,
            "siblings_details": "1 brother, works abroad",
            "family_values": "Modern",
            "industry": "Finance",
            "education": "MBA Finance, IIM Bangalore",
            "current_designation": "Vice President - Investments",
            "current_company": "HDFC Capital Advisors",
            "annual_income_min": "2500000.00",
            "annual_income_max": "3500000.00",
            "income_unit": "INR",
            "date_of_birth": "1996-01-30",
            "time_of_birth": "09:00:00",
            "birth_place": "Bangalore",
            "zodiac_sign": "Aquarius",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 28, "age_max": 35,
            "height_min_cm": 172, "height_max_cm": 188,
            "religion": "Hindu",
            "location": "Bangalore, Mumbai, Delhi",
            "education": "Post Graduate (IIT/IIM preferred)",
            "min_income": "2000000.00",
            "income_unit": "INR",
            "family_values": "Modern",
        },
    },
    {
        "email": "arjun@milansetu.test",
        "phone": "9100000007",
        "password": "Test@1234",
        "user_type": UserType.BASIC,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Arjun Patel",
            "age": 30,
            "height_cm": 176,
            "religion": "Hindu",
            "mother_tongue": "Gujarati",
            "marital_status": "Never Married",
            "father_occupation": "Shop Owner",
            "mother_occupation": "Homemaker",
            "siblings_count": 2,
            "siblings_details": "2 sisters, both married",
            "family_values": "Traditional",
            "industry": "Finance",
            "education": "B.Com, Gujarat University",
            "current_designation": "Senior Accountant",
            "current_company": "Deloitte India",
            "annual_income_min": "700000.00",
            "annual_income_max": "900000.00",
            "income_unit": "INR",
            "date_of_birth": "1994-06-05",
            "time_of_birth": "11:30:00",
            "birth_place": "Ahmedabad",
            "zodiac_sign": "Gemini",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 24, "age_max": 28,
            "height_min_cm": 155, "height_max_cm": 168,
            "religion": "Hindu",
            "location": "Ahmedabad, Surat, Mumbai",
        },
    },
    {
        "email": "sneha@milansetu.test",
        "phone": "9100000008",
        "password": "Test@1234",
        "user_type": UserType.SILVER,
        "role": UserRole.USER,
        "profile": {
            "full_name": "Sneha Kapoor",
            "age": 27,
            "height_cm": 162,
            "religion": "Hindu",
            "mother_tongue": "Punjabi",
            "marital_status": "Never Married",
            "father_occupation": "Army Officer (Retd.)",
            "mother_occupation": "Lecturer",
            "siblings_count": 1,
            "siblings_details": "1 brother, CA",
            "family_values": "Traditional",
            "industry": "Architecture & Design",
            "education": "B.Arch, SPA Delhi",
            "current_designation": "Lead Architect",
            "current_company": "Studio 9 Design, New Delhi",
            "annual_income_min": "1000000.00",
            "annual_income_max": "1400000.00",
            "income_unit": "INR",
            "date_of_birth": "1997-12-03",
            "time_of_birth": "16:00:00",
            "birth_place": "New Delhi",
            "zodiac_sign": "Sagittarius",
            "manglik_status": "Non-Manglik",
        },
        "ideal_partner": {
            "age_min": 28, "age_max": 34,
            "height_min_cm": 170, "height_max_cm": 185,
            "religion": "Hindu",
            "location": "Delhi, Gurgaon, Noida, Mumbai",
            "education": "Graduation or above",
            "family_values": "Traditional",
        },
    },
]

# Interests to create: (sender_email, receiver_email, status, message)
INTERESTS = [
    # Aditya → females
    ("aditya@milansetu.test", "ananya@milansetu.test", "pending",    "Hi Ananya! Your profile resonates with my values. I'd love to connect."),
    ("aditya@milansetu.test", "priya@milansetu.test",  "accepted",   "Hello Priya, I noticed we share similar family values and goals."),
    ("aditya@milansetu.test", "deepika@milansetu.test","pending",    "Hi Deepika! Your professional journey is inspiring. Would love to know you better."),
    ("aditya@milansetu.test", "sneha@milansetu.test",  "declined",   "Hi Sneha, I think we'd be a great match!"),
    # Ravi → females
    ("ravi@milansetu.test", "priya@milansetu.test",    "pending",    "Hello, I think our backgrounds are very compatible."),
    ("ravi@milansetu.test", "ananya@milansetu.test",   "pending",    "Hi Ananya, hope we can connect and know each other."),
    # Sai → females
    ("sai@milansetu.test",  "priya@milansetu.test",    "accepted",   "Hello Priya, I am interested in your profile."),
    ("sai@milansetu.test",  "sneha@milansetu.test",    "pending",    "Hi Sneha!"),
    # Arjun → females
    ("arjun@milansetu.test", "ananya@milansetu.test",  "pending",    "Hello, I'd love to connect."),
    ("arjun@milansetu.test", "deepika@milansetu.test", "pending",    "Hi Deepika, I admire your profile greatly."),
]


class Command(BaseCommand):
    help = "Seeds test users, profiles, ideal partners and interests for development testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n[*] Seeding MilanSetu test data...\n"))

        created_users = {}  # email -> User object

        with transaction.atomic():
            # ----------------------------------------------------------------
            for data in USERS_DATA:
                email = data["email"]
                if User.objects.filter(email=email).exists():
                    user = User.objects.get(email=email)
                    self.stdout.write(f"  [!] User {email} already exists -- skipping user creation")
                else:
                    user = User.objects.create_user(
                        email=email,
                        password=data["password"],
                        phone=data["phone"],
                        user_type=data["user_type"],
                        role=data["role"],
                    )
                    # Set premium timestamps for premium users
                    if data["user_type"] != UserType.BASIC:
                        user.premium_since = timezone.now()
                        user.premium_expires_at = timezone.now() + timezone.timedelta(days=365)
                        user.save()
                    self.stdout.write(f"  [+] Created user: {email} ({data['user_type']})")

                created_users[email] = user

                # Profile
                profile_data = data["profile"]
                if not ProfileDetails.objects.filter(user=user).exists():
                    ProfileDetails.objects.create(user=user, **profile_data)
                    self.stdout.write(f"     -> Profile: {profile_data['full_name']}")

                # Ideal Partner
                ideal_data = data.get("ideal_partner", {})
                if ideal_data and not IdealPartner.objects.filter(user=user).exists():
                    IdealPartner.objects.create(user=user, **ideal_data)
                    self.stdout.write(f"     -> Ideal partner preferences set")

            # ----------------------------------------------------------------
            self.stdout.write("\n[*] Creating interest connections...\n")
            for sender_email, receiver_email, status, message in INTERESTS:
                sender = created_users.get(sender_email)
                receiver_user = created_users.get(receiver_email)
                if not sender or not receiver_user:
                    continue
                try:
                    receiver_profile = ProfileDetails.objects.get(user=receiver_user)
                except ProfileDetails.DoesNotExist:
                    continue

                if SentInterest.objects.filter(sender=sender, receiver_profile=receiver_profile).exists():
                    self.stdout.write(f"  [!] Interest {sender_email} -> {receiver_email} already exists")
                    continue

                SentInterest.objects.create(
                    sender=sender,
                    receiver_profile=receiver_profile,
                    status=status,
                    message=message,
                    match_score=75,
                )
                self.stdout.write(f"  [+] {sender_email} -> {receiver_email} [{status}]")

        self.stdout.write(self.style.SUCCESS(
            "\n[DONE] Test data seeded successfully.\n\n"
            "Login with any of these accounts (password: Test@1234):\n"
            "  aditya@milansetu.test  -- Gold Premium, Software Architect\n"
            "  ananya@milansetu.test  -- Silver Premium, Corporate Lawyer\n"
            "  ravi@milansetu.test    -- Basic, Teacher\n"
            "  priya@milansetu.test   -- Basic, Doctor\n"
            "  sai@milansetu.test     -- Basic, Engineer\n"
            "  deepika@milansetu.test -- Platinum Premium, Finance VP\n"
            "  arjun@milansetu.test   -- Basic, Accountant\n"
            "  sneha@milansetu.test   -- Silver Premium, Architect\n"
        ))
