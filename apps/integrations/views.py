from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def list_integrations(request):
    integrations = request.user.integrations.all()
    return render(request, "integrations/list.html", {"integrations": integrations})
