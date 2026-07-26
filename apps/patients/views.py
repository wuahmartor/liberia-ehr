from django.shortcuts import render

def search_results(request):
    query = request.GET.get("q", "").strip()
    patients = []
    return render(
        request,
        "partials/patients/search_results.html",
        {
            "query": query,
            "patients": patients,
        },
    )
