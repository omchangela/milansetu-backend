from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.http import JsonResponse
from django.db import connection

def health_check(request):
    db_status = "ok"
    db_tables = []
    error = None
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_tables = connection.introspection.table_names()
    except Exception as e:
        import traceback
        db_status = "error"
        error = f"{str(e)}\n{traceback.format_exc()}"
    return JsonResponse({
        "status": "ok" if db_status == "ok" else "error",
        "database": db_status,
        "engine": connection.settings_dict.get('ENGINE'),
        "host": connection.settings_dict.get('HOST'),
        "name": connection.settings_dict.get('NAME'),
        "tables_count": len(db_tables),
        "has_users_table": "users" in db_tables,
        "error": error,
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/auth/', include('authentication.urls')),
    path('api/users/', include('users.urls')),
    path('api/milansetu/', include('milansetu.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
