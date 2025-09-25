from notes.views import NotesView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'notes', NotesView, basename='notes')

urlpatterns = router.urls
