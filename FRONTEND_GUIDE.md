# راهنمای فرانت‌اند

این راهنما به توسعه‌دهندگان فرانت‌اند کمک می‌کند تا بفهمند در هر صفحه از اپلیکیشن، باید از کدام اندپوینت‌ها استفاده کنند.

## احراز هویت

- **ثبت‌نام**: `POST /auth/users/`
- **ورود با رمز عبور**: `POST /auth/jwt/create/`
- **ورود با OTP**:
    - `POST /api/users/send_otp/` (برای ارسال کد)
    - `POST /api/users/verify_otp/` (برای تایید کد)
- **خروج**: (کلاینت باید توکن JWT را حذف کند)
- **حذف اکانت**: `DELETE /auth/users/me/`
- **بازیابی رمز ورود**:
    - `POST /auth/users/reset_password/`
    - `POST /auth/users/reset_password_confirm/`

## داشبورد کاربر

- **نمایش اطلاعات داشبورد**: `GET /api/users/dashboard/`
  - **مسابقات آینده**: `upcoming_tournaments`
  - **درخواست‌های عضویت ارسالی**: `sent_invitations`
  - **درخواست‌های عضویت دریافتی**: `received_invitations`
  - **آخرین تراکنش‌ها**: `latest_transactions`

## تیم‌ها

- **ایجاد تیم**: `POST /api/teams/`
- **مشاهده لیست تیم‌ها**: `GET /api/teams/`
- **مشاهده جزئیات تیم**: `GET /api/teams/{id}/`
- **دعوت عضو به تیم**: `POST /api/teams/{id}/invite_member/`
- **پاسخ به دعوت‌نامه**: `POST /api/teams/respond-invitation/`
- **خروج از تیم**: `POST /api/teams/{id}/leave_team/`
- **اخراج عضو از تیم**: `POST /api/teams/{id}/remove_member/`

## مسابقات

- **مشاهده لیست مسابقات**: `GET /api/tournaments/`
- **مشاهده جزئیات مسابقه**: `GET /api/tournaments/{id}/`
- **ثبت‌نام در مسابقه انفرادی**: `POST /api/tournaments/{id}/join/`
- **ثبت‌نام در مسابقه تیمی**: `POST /api/tournaments/{id}/join/` (با ارسال `team_id` و `member_ids`)
- **گزارش تخلف در مسابقه**: `POST /api/reports/`
- **ارسال ویدیو توسط برنده**: `POST /api/winner-submissions/`

## پشتیبانی

- **ایجاد تیکت پشتیبانی**: `POST /api/support/tickets/`
- **مشاهده لیست تیکت‌ها**: `GET /api/support/tickets/`
- **مشاهده جزئیات تیکت**: `GET /api/support/tickets/{id}/`
- **ارسال پیام در تیکت**: `POST /api/support/tickets/{ticket_pk}/messages/`
- **مشاهده پیام‌های تیکت**: `GET /api/support/tickets/{ticket_pk}/messages/`
