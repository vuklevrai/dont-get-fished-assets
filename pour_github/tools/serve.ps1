param([string]$Root, [int]$Port = 8765)
$types = @{ ".png" = "image/png"; ".html" = "text/html; charset=utf-8"; ".js" = "text/javascript"; ".glb" = "model/gltf-binary"; ".json" = "application/json" }
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
"listening on $Port"
while ($true) {
  $ctx = $listener.GetContext()
  $name = [System.IO.Path]::GetFileName($ctx.Request.Url.AbsolutePath)
  $path = Join-Path $Root $name
  if ($name -and (Test-Path $path -PathType Leaf)) {
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $ext = [System.IO.Path]::GetExtension($path)
    if ($types.ContainsKey($ext)) { $ctx.Response.ContentType = $types[$ext] }
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } else {
    $ctx.Response.StatusCode = 404
  }
  $ctx.Response.Close()
}
