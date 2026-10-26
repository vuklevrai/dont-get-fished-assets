-- Client-side shared state (one table per client): open UIs, settings and camera effects.
local ClientState = {
	openUis = {}, -- name -> true while a UI needs the mouse
	backpedal = false, -- S swims backwards without turning around
	shakeUntil = 0,
	shakeStrength = 0,
	changed = Instance.new("BindableEvent"),
}

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
	local left = ClientState.shakeUntil - os.clock()
	if left <= 0 then
		return Vector3.zero
	end
	local s = ClientState.shakeStrength * math.min(1, left * 6)
	return Vector3.new((math.random() - 0.5) * s, (math.random() - 0.5) * s, (math.random() - 0.5) * s)
end

return ClientState
