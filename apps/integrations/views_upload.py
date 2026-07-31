from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.integrations.forms import StatementUploadForm
from apps.integrations.importers import parse_bank_statement, import_statement_rows


@login_required
def upload_statement(request):
    if request.method == "POST":
        form = StatementUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            account = form.cleaned_data["account"]
            uploaded = form.cleaned_data["file"]
            try:
                csv_text = uploaded.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                messages.error(request, "File could not be decoded as UTF-8 text.")
                return render(request, "integrations/upload.html", {"form": form})
            try:
                rows = parse_bank_statement(csv_text)
            except ValueError as exc:
                messages.error(request, str(exc))
                return render(request, "integrations/upload.html", {"form": form})
            if not rows:
                messages.error(request, "No transactions found in the uploaded file.")
                return render(request, "integrations/upload.html", {"form": form})
            imported, errors = import_statement_rows(request.user, account, rows)
            if errors:
                messages.warning(request, "{} error(s) encountered.".format(len(errors)))
            messages.success(request, "Imported {} transaction(s).".format(imported))
            return render(
                request,
                "integrations/upload.html",
                {"form": form, "imported": imported, "errors": errors, "total": len(rows)},
            )
    else:
        form = StatementUploadForm(user=request.user)
    return render(request, "integrations/upload.html", {"form": form})
