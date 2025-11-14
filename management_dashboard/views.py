from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
# TODO: The SeedDataForm and the run_seed_data_task are part of an incomplete feature.
# This code should be uncommented and finalized once the seeding logic is implemented.
# from tournaments.forms import SeedDataForm
# from tournaments.tasks import run_seed_data_task

# @user_passes_test(lambda u: u.is_staff)
# def seed_data_view(request):
#     """
#     A view for staff users to trigger the data seeding process.
#     """
#     if request.method == 'POST':
#         form = SeedDataForm(request.POST)
#         if form.is_valid():
#             options = form.cleaned_data
#             # Celery task expects a dictionary of options
#             run_seed_data_task.delay(**options)
#             messages.success(request, 'داده‌سازی در پس‌زمینه شروع شد. این فرآیند ممکن است چند دقیقه طول بکشد.')
#             return redirect('management_dashboard:seed_data')
#     else:
#         form = SeedDataForm()

#     return render(request, 'management_dashboard/seed_data.html', {'form': form})
