import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _  # Enables i18n support

class HIPAAPasswordValidator:
    def validate(self, password: str, user=None) -> None:
        if len(password) < 12:
            raise ValidationError(_("Password must be at least 12 characters long."))
        
        if len(re.findall(r'[A-Z]', password)) < 2:
            raise ValidationError(_("Password must contain at least 2 uppercase letters."))
        
        if len(re.findall(r'[a-z]', password)) < 2:
            raise ValidationError(_("Password must contain at least 2 lowercase letters."))
        
        if len(re.findall(r'\d', password)) < 2:
            raise ValidationError(_("Password must contain at least 2 digits."))
        
        # More inclusive special characters regex
        if len(re.findall(r'[^A-Za-z0-9]', password)) < 2:
            raise ValidationError(_("Password must contain at least 2 special characters."))

    def get_help_text(self) -> str:
        return _(
            "Your password must be at least 12 characters long and include at least "
            "2 uppercase letters, 2 lowercase letters, 2 digits, and 2 special characters."
        )
