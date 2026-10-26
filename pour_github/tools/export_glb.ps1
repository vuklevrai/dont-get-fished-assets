param([string]$Path, [string]$Out)
# Converts a blocky glTF fish into a Luau ModuleScript describing boxes per rig segment.
Add-Type -Path (Join-Path $PSScriptRoot "Voxelize.cs")
$inv = [System.Globalization.CultureInfo]::InvariantCulture
function F($v) { return ([double]$v).ToString("0.####", $inv) }

$b = [System.IO.File]::ReadAllBytes($Path)
$jsonLen = [BitConverter]::ToUInt32($b, 12)
$g = [System.Text.Encoding]::UTF8.GetString($b, 20, $jsonLen) | ConvertFrom-Json
$binStart = 20 + $jsonLen + 8
$bin = New-Object byte[] ($b.Length - $binStart)
[Array]::Copy($b, $binStart, $bin, 0, $bin.Length)

$SEGMENTS = @("tete", "corps_avant", "corps_arriere", "queue_1", "queue_2", "nageoire_caudale",
              "nageoire_dorsale", "nageoire_pectorale_g", "nageoire_pectorale_d")

# parent map
$parent = @{}
for ($n = 0; $n -lt $g.nodes.Count; $n++) { foreach ($c in @($g.nodes[$n].children)) { if ($null -ne $c) { $parent[[int]$c] = $n } } }

# quaternion helpers (x,y,z,w)
function QMul($a, $q) {
  return @(
    ($a[3]*$q[0] + $a[0]*$q[3] + $a[1]*$q[2] - $a[2]*$q[1]),
    ($a[3]*$q[1] - $a[0]*$q[2] + $a[1]*$q[3] + $a[2]*$q[0]),
    ($a[3]*$q[2] + $a[0]*$q[1] - $a[1]*$q[0] + $a[2]*$q[3]),
    ($a[3]*$q[3] - $a[0]*$q[0] - $a[1]*$q[1] - $a[2]*$q[2]))
}
function QRot($q, $v) {
  $p = @($v[0], $v[1], $v[2], 0.0)
  $qc = @(-$q[0], -$q[1], -$q[2], $q[3])
  $r = QMul (QMul $q $p) $qc
  return @($r[0], $r[1], $r[2])
}
# world transform of node n: returns @(pos, quat)
function World($n) {
  $node = $g.nodes[$n]
  $t = @(0.0, 0.0, 0.0); if ($node.translation) { $t = @([double]$node.translation[0], [double]$node.translation[1], [double]$node.translation[2]) }
  $r = @(0.0, 0.0, 0.0, 1.0); if ($node.rotation) { $r = @([double]$node.rotation[0], [double]$node.rotation[1], [double]$node.rotation[2], [double]$node.rotation[3]) }
  if (-not $parent.ContainsKey($n)) { return ,@($t, $r) }
  $pw = World $parent[$n]
  $pt = QRot $pw[1] $t
  return ,@(@(($pw[0][0] + $pt[0]), ($pw[0][1] + $pt[1]), ($pw[0][2] + $pt[2])), (QMul $pw[1] $r))
}
function SegmentOf($n) {
  $cur = $n
  while ($true) {
    if ($SEGMENTS -contains $g.nodes[$cur].name) { return $g.nodes[$cur].name }
    if (-not $parent.ContainsKey($cur)) { return "centre" }
    $cur = $parent[$cur]
  }
}
function ToSrgb($c) { if ($c -le 0.0031308) { return 12.92 * $c } else { return 1.055 * [Math]::Pow($c, 1 / 2.4) - 0.055 } }

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("-- Generated from bonite_brainrot.glb: boxes per rig segment, in model units (fish faces +X).")
[void]$sb.AppendLine("return {")
[void]$sb.AppendLine("`tcolors = {")
foreach ($m in $g.materials) {
  $f = $m.pbrMetallicRoughness.baseColorFactor
  $rgb = @(0..2 | ForEach-Object { [Math]::Round((ToSrgb ([double]$f[$_])) * 255) })
  [void]$sb.AppendLine("`t`t$($m.name) = Color3.fromRGB($($rgb -join ', ')),")
}
[void]$sb.AppendLine("`t},")
[void]$sb.AppendLine("`tsegments = {")
for ($n = 0; $n -lt $g.nodes.Count; $n++) {
  $nm = $g.nodes[$n].name
  if ($SEGMENTS -contains $nm) {
    $w = World $n
    $p = $parent[$n]; $pseg = if ($p -ne $null) { SegmentOf $p } else { "centre" }
    [void]$sb.AppendLine("`t`t$nm = { parent = `"$pseg`", pos = Vector3.new($(F $w[0][0]), $(F $w[0][1]), $(F $w[0][2])), rot = { $(F $w[1][0]), $(F $w[1][1]), $(F $w[1][2]), $(F $w[1][3]) } },")
  }
}
[void]$sb.AppendLine("`t},")
[void]$sb.AppendLine("`tpieces = {")
$totalBoxes = 0; $report = @()
for ($n = 0; $n -lt $g.nodes.Count; $n++) {
  $node = $g.nodes[$n]
  if ($null -eq $node.mesh) { continue }
  $prim = $g.meshes[$node.mesh].primitives[0]
  $pa = $g.accessors[$prim.attributes.POSITION]; $pv = $g.bufferViews[$pa.bufferView]
  $ia = $g.accessors[$prim.indices]; $iv = $g.bufferViews[$ia.bufferView]
  $posOff = [int]$pv.byteOffset + [int]$pa.byteOffset
  $idxOff = [int]$iv.byteOffset + [int]$ia.byteOffset
  $tris = [int]$ia.count / 3
  $boxes = New-Object System.Collections.Generic.List[double[]]
  $mis = 0
  if ($tris -le 48 -and $tris % 12 -eq 0 -and [int]$pa.count -eq $tris * 2) {
    # plain boxes (three.js BoxGeometry): 24 consecutive vertices per box
    for ($bi = 0; $bi -lt $pa.count / 24; $bi++) {
      $c = $null
      for ($v = $bi * 24; $v -lt ($bi + 1) * 24; $v++) {
        $x = [BitConverter]::ToSingle($bin, $posOff + 12*$v); $y = [BitConverter]::ToSingle($bin, $posOff + 12*$v + 4); $z = [BitConverter]::ToSingle($bin, $posOff + 12*$v + 8)
        if ($null -eq $c) { $c = @($x, $y, $z, $x, $y, $z) }
        $c[0] = [Math]::Min($c[0], $x); $c[1] = [Math]::Min($c[1], $y); $c[2] = [Math]::Min($c[2], $z)
        $c[3] = [Math]::Max($c[3], $x); $c[4] = [Math]::Max($c[4], $y); $c[5] = [Math]::Max($c[5], $z)
      }
      $boxes.Add([double[]]$c)
    }
  } else {
    $spans = [Voxelize]::Columns($bin, $posOff, [int]$pa.count, $idxOff, [int]$ia.count, [int]$ia.componentType, [ref]$mis)
    foreach ($bx in [Voxelize]::Merge($spans)) { $boxes.Add($bx) }
  }
  $w = World $n
  $seg = SegmentOf $n
  $mat = $g.materials[$prim.material].name
  $report += "{0,-32} seg={1,-20} mat={2,-9} boxes={3,3} mismatched={4}" -f $node.name, $seg, $mat, $boxes.Count, $mis
  $totalBoxes += $boxes.Count
  [void]$sb.AppendLine("`t`t{ name = `"$($node.name)`", seg = `"$seg`", mat = `"$mat`", pos = Vector3.new($(F $w[0][0]), $(F $w[0][1]), $(F $w[0][2])), rot = { $(F $w[1][0]), $(F $w[1][1]), $(F $w[1][2]), $(F $w[1][3]) }, boxes = {")
  foreach ($bx in $boxes) { [void]$sb.AppendLine("`t`t`t{ $(($bx | ForEach-Object { F $_ }) -join ', ') },") }
  [void]$sb.AppendLine("`t`t} },")
}
[void]$sb.AppendLine("`t},")
[void]$sb.AppendLine("}")
[System.IO.File]::WriteAllText($Out, $sb.ToString())
$report
"TOTAL boxes = $totalBoxes"
