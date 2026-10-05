$cities = @(
  @{ name = "Paris";     lat = 48.85; lon = 2.35 },
  @{ name = "Lyon";      lat = 45.76; lon = 4.84 },
  @{ name = "Marseille"; lat = 43.30; lon = 5.37 }
)
$ports = 8080, 8081, 8082

foreach ($c in $cities) {
  $url = "https://api.open-meteo.com/v1/forecast?latitude=$($c.lat)&longitude=$($c.lon)&current=temperature_2m,relative_humidity_2m"
  $w = Invoke-RestMethod $url
  $value = "temperature=$($w.current.temperature_2m) humidity=$($w.current.relative_humidity_2m)"
  $body = @{ key = "weather-$($c.name)"; value = $value } | ConvertTo-Json
  Write-Host "==> $($c.name) : $value"
  foreach ($p in $ports) {
    try {
      Invoke-RestMethod -Method Post -Uri "http://localhost:$p/data" -ContentType "application/json" -Body $body | Out-Null
      Write-Host "   port $p : OK"
    } catch {
      Write-Host "   port $p : ECHEC"
    }
  }
}

Write-Host ""
Write-Host "==> Verification"
foreach ($p in $ports) {
  Write-Host "--- port $p"
  Invoke-RestMethod "http://localhost:$p/data" | ConvertTo-Json -Depth 5
}