param([string]$Path)
Add-Type -Path (Join-Path $PSScriptRoot "Voxelize.cs")
$b = [System.IO.File]::ReadAllBytes($Path)
$jsonLen = [BitConverter]::ToUInt32($b, 12)
$g = [System.Text.Encoding]::UTF8.GetString($b, 20, $jsonLen) | ConvertFrom-Json
$binStart = 20 + $jsonLen + 8
$bin = New-Object byte[] ($b.Length - $binStart)
[Array]::Copy($b, $binStart, $bin, 0, $bin.Length)

for ($n = 0; $n -lt $g.nodes.Count; $n++) {
  $node = $g.nodes[$n]
  if ($null -eq $node.mesh) { continue }
  $prim = $g.meshes[$node.mesh].primitives[0]
  $pa = $g.accessors[$prim.attributes.POSITION]; $pv = $g.bufferViews[$pa.bufferView]
  $ia = $g.accessors[$prim.indices]; $iv = $g.bufferViews[$ia.bufferView]
  $posOff = [int]$pv.byteOffset + [int]$pa.byteOffset
  $idxOff = [int]$iv.byteOffset + [int]$ia.byteOffset
  $cells = [Voxelize]::Cells($bin, $posOff, [int]$pa.count, $idxOff, [int]$ia.count, [int]$ia.componentType)
  $faces = ($cells.Values | Measure-Object -Sum).Sum
  "{0,-32} mat={1,-9} tris={2,5} cells={3,4} faces={4,5}" -f $node.name, $g.materials[$prim.material].name, ($ia.count/3), $cells.Count, $faces
}
