-- Client-side shared state (one table per client): open UIs, settings, camera effects and the local fish's swim.
local ClientState = {
	openUis = {}, -- name -> true while a UI needs the mouse
	backpedal = false, -- S swims backwards without turning around
	shakeUntil = 0,
	shakeStrength = 0,
	changed = Instance.new("BindableEvent"),
	-- written by FishController every frame, read by FishAnimator (tail beat in sync with the swim)
	swimModel = nil :: Model?,
	swimIntensity = 0, -- 0 idle .. 1 full swim (up to 1.3 when thrashing)
	swimPhase = 0, -- 0..1 position in the tail stroke
}

-- shakes follow smooth noise: the camera wobbles, it never jumps to random positions frame by frame
local SHAKE_FREQUENCY = 14 -- noise samples per second
local shakeAmp, lastSample = 0, os.clock()

function ClientState.setUiOpen(name: string, open: boolean)
	ClientState.openUis[name] = open or nil
	ClientState.changed:Fire()
end

function ClientState.uiOpen(): boolean
	return next(ClientState.openUis) ~= nil
end

function ClientState.shake(strength: number, duration: number)
	ClientState.shakeStrength = math.max(strength, os.clock() < ClientState.shakeUntil and ClientState.shakeStrength or 0)
	ClientState.shakeUntil = math.max(ClientState.shakeUntil, os.clock() + duration)
end

function ClientState.shakeOffset(): Vector3
	local now = os.clock()
	local dt = math.clamp(now - lastSample, 0, 0.1)
	lastSample = now
	local left = ClientState.shakeUntil - now
	local wanted = if left > 0 then ClientState.shakeStrength * math.min(1, left * 6) else 0
	-- the strength itself eases in and out, so starting or stacking a shake never pops the camera
	shakeAmp += (wanted - shakeAmp) * (1 - math.exp(-30 * dt))
	if shakeAmp < 1e-3 then
		return Vector3.zero
	end
	local t = now * SHAKE_FREQUENCY
	return Vector3.new(math.noise(t, 11.3, 0.5), math.noise(4.7, t, 23.1), math.noise(19.9, 7.1, t)) * (shakeAmp * 1.4)
end

return ClientState
