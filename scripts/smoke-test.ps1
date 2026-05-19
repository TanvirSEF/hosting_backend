param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Email = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        $Body = $null
    )

    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $Headers
        TimeoutSec = 10
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    Invoke-RestMethod @params
}

Write-Host "Checking health..."
$health = Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/health/diagnostics"
Write-Host "Health: $($health.overall_status)"

Write-Host "Checking public hosting packages..."
$packages = Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/hosting/packages"
Write-Host "Packages visible: $($packages.Count)"

if ($Email -and $Password) {
    Write-Host "Logging in..."
    $login = Invoke-Json -Method "POST" -Url "$BaseUrl/api/v1/auth/login" -Body @{
        email = $Email
        password = $Password
    }
    $headers = @{ Authorization = "Bearer $($login.access_token)" }

    Write-Host "Checking /me..."
    $me = Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/auth/me" -Headers $headers
    Write-Host "Authenticated as: $($me.email)"

    Write-Host "Checking my invoices/services/domains..."
    Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/billing/my-invoices" -Headers $headers | Out-Null
    Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/hosting/my-services" -Headers $headers | Out-Null
    Invoke-Json -Method "GET" -Url "$BaseUrl/api/v1/domain/my-domains" -Headers $headers | Out-Null
}

Write-Host "Smoke test completed."
