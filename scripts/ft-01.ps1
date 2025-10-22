Param(
  [string]$ApiKey = "changeme"
)

Write-Host "FT-01 Test: Payment authorize should fail; order canceled"

$headers = @{ 'X-API-Key' = $ApiKey; 'Content-Type' = 'application/json' }

Write-Host "1) Fetch menus (through WAF)"
try {
  $menus = Invoke-RestMethod -Uri "http://localhost:8080/api/restaurants/menus" -Headers $headers -Method GET
  Write-Host (ConvertTo-Json $menus)
} catch { Write-Host $_; }

Write-Host "2) Create order"
$orderBody = @{
  customer_id = "c-ps1"
  items = @(
    @{ name = "Pizza Margherita"; price = 10.5; quantity = 1 },
    @{ name = "Caesar Salad";    price = 8.5;  quantity = 1 }
  )
} | ConvertTo-Json

try {
  $resp = Invoke-RestMethod -Uri "http://localhost:8080/api/orders/orders" -Headers $headers -Method POST -Body $orderBody
  Write-Host (ConvertTo-Json $resp)
  $orderId = $resp.id
} catch {
  Write-Host $_
}

if ($null -ne $orderId) {
  Start-Sleep -Seconds 1
  Write-Host "3) Get order status"
  try {
    $status = Invoke-RestMethod -Uri "http://localhost:8080/api/orders/orders/$orderId" -Headers $headers -Method GET
    Write-Host (ConvertTo-Json $status)
  } catch { Write-Host $_ }
}

