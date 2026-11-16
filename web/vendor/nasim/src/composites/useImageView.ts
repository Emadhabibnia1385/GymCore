'use client';

import {
  type KeyboardEvent,
  type PointerEvent,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from 'react';
import {
  anchoredPan,
  clampPan,
  clampScale,
  distance,
  MAX_SCALE,
  midpoint,
  MIN_SCALE,
  type Point,
  stepScale,
} from './viewerMath';

// The picture is drawn as translate, rotate, scale: the pan is in screen pixels, `turns` counts quarter
// turns without wrapping (so a turn never spins back), `fit` shrinks a picture lying on its side to the stage.
export type View = { scale: number; pan: Point; turns: number; fit: number };

const ORIGIN: Point = { x: 0, y: 0 };
const HOME: View = { scale: MIN_SCALE, pan: ORIGIN, turns: 0, fit: 1 };
const PAN_STEP = 48;
const DOUBLE_ZOOM = 2.5;
const WHEEL = 0.002;
const PINCH_WHEEL = 0.01;

type Gesture =
  | { kind: 'pan'; id: number; from: Point; pan: Point }
  | {
      kind: 'pinch';
      ids: [number, number];
      gap: number;
      middle: Point;
      scale: number;
      pan: Point;
    };

// The view at another scale, the point under `anchor` staying where it is; at the fit it is centred.
function scaledTo(now: View, to: number, anchor: Point): View {
  const scale = clampScale(to);
  return {
    ...now,
    scale,
    pan:
      scale === MIN_SCALE
        ? ORIGIN
        : anchoredPan(now.pan, anchor, now.scale, scale),
  };
}

export function transformOf(view: View): string {
  const { pan, turns, scale, fit } = view;
  return `translate(${pan.x}px, ${pan.y}px) rotate(${turns * 90}deg) scale(${scale * fit})`;
}

// What the viewer does to its picture: buttons, keys, the wheel, a drag and two fingers all end here.
export function useImageView() {
  const [view, setView] = useState<View>(HOME);
  const [gesturing, setGesturing] = useState(false);
  const stage = useRef<HTMLDivElement | null>(null);
  const image = useRef<HTMLImageElement | null>(null);
  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<Gesture | null>(null);

  // Sizes are read when something moves, never while rendering; a stage with no size yet (or no
  // layout at all) is not measured and the picture is then not held back.
  function measure() {
    const frame = stage.current;
    const picture = image.current;
    if (!frame || !picture) return null;
    const stageSize = { w: frame.clientWidth, h: frame.clientHeight };
    const imageSize = { w: picture.offsetWidth, h: picture.offsetHeight };
    if (!stageSize.w || !stageSize.h || !imageSize.w || !imageSize.h)
      return null;
    return { stage: stageSize, image: imageSize };
  }

  function limited(next: View): View {
    const size = measure();
    if (!size) return next;
    const sideways = next.turns % 2 !== 0;
    const zoom = next.scale * next.fit;
    const content = {
      w: (sideways ? size.image.h : size.image.w) * zoom,
      h: (sideways ? size.image.w : size.image.h) * zoom,
    };
    return { ...next, pan: clampPan(next.pan, content, size.stage) };
  }

  function fitFor(turns: number): number {
    const size = measure();
    if (!size || turns % 2 === 0) return 1;
    return Math.min(
      1,
      size.stage.h / size.image.w,
      size.stage.w / size.image.h,
    );
  }

  // A point of the screen measured from the stage's centre, which is where the picture turns.
  function fromCentre(x: number, y: number): Point {
    const box = stage.current?.getBoundingClientRect();
    if (!box) return { x, y };
    return {
      x: x - (box.left + box.width / 2),
      y: y - (box.top + box.height / 2),
    };
  }

  function zoomTo(scale: number, anchor: Point = ORIGIN) {
    setView((now) => limited(scaledTo(now, scale, anchor)));
  }

  function step(direction: 1 | -1) {
    setView((now) =>
      limited(scaledTo(now, stepScale(now.scale, direction), ORIGIN)),
    );
  }

  function rotate() {
    setView((now) => {
      const turns = now.turns + 1;
      return { ...now, turns, fit: fitFor(turns), pan: ORIGIN };
    });
  }

  // Home again, the short way round: a picture turned three quarters comes back through the fourth.
  function reset() {
    setView((now) => ({ ...HOME, turns: Math.round(now.turns / 4) * 4 }));
  }

  function panBy(dx: number, dy: number) {
    setView((now) =>
      now.scale > MIN_SCALE
        ? limited({ ...now, pan: { x: now.pan.x + dx, y: now.pan.y + dy } })
        : now,
    );
  }

  // The wheel: a notch zooms by a few percent, a trackpad pinch (a wheel with the control key) faster.
  // It is a native listener because React's own is passive and could not keep the page still.
  const onWheel = useEffectEvent((event: WheelEvent) => {
    event.preventDefault();
    const speed = event.ctrlKey ? PINCH_WHEEL : WHEEL;
    const factor = Math.exp(-event.deltaY * speed);
    const anchor = fromCentre(event.clientX, event.clientY);
    setView((now) => limited(scaledTo(now, now.scale * factor, anchor)));
  });
  useEffect(() => {
    const node = stage.current;
    if (!node) return;
    const listener = (event: WheelEvent) => onWheel(event);
    node.addEventListener('wheel', listener, { passive: false });
    return () => node.removeEventListener('wheel', listener);
  }, []);

  function begin() {
    const points = [...pointers.current.entries()];
    if (points.length >= 2) {
      const [[idA, a], [idB, b]] = points as [[number, Point], [number, Point]];
      gesture.current = {
        kind: 'pinch',
        ids: [idA, idB],
        gap: distance(a, b) || 1,
        middle: midpoint(a, b),
        scale: view.scale,
        pan: view.pan,
      };
    } else if (points.length === 1 && view.scale > MIN_SCALE) {
      const [[id, point]] = points as [[number, Point]];
      gesture.current = { kind: 'pan', id, from: point, pan: view.pan };
    } else {
      gesture.current = null;
    }
  }

  function onPointerDown(event: PointerEvent<HTMLElement>) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    pointers.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    event.currentTarget.setPointerCapture?.(event.pointerId);
    begin();
    setGesturing(true);
  }

  function onPointerMove(event: PointerEvent<HTMLElement>) {
    const current = gesture.current;
    if (!pointers.current.has(event.pointerId) || !current) return;
    pointers.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    if (current.kind === 'pan') {
      const point = pointers.current.get(current.id);
      if (!point) return;
      const pan = {
        x: current.pan.x + point.x - current.from.x,
        y: current.pan.y + point.y - current.from.y,
      };
      setView((now) => limited({ ...now, pan }));
      return;
    }
    const a = pointers.current.get(current.ids[0]);
    const b = pointers.current.get(current.ids[1]);
    if (!a || !b) return;
    const scale = clampScale((current.scale * distance(a, b)) / current.gap);
    const was = fromCentre(current.middle.x, current.middle.y);
    const middle = midpoint(a, b);
    const held = anchoredPan(current.pan, was, current.scale, scale);
    const pan =
      scale === MIN_SCALE
        ? ORIGIN
        : {
            x: held.x + middle.x - current.middle.x,
            y: held.y + middle.y - current.middle.y,
          };
    setView((state) => limited({ ...state, scale, pan }));
  }

  function onPointerEnd(event: PointerEvent<HTMLElement>) {
    if (!pointers.current.delete(event.pointerId)) return;
    // one finger left after a pinch carries on as a drag from where it is
    begin();
    if (pointers.current.size === 0) setGesturing(false);
  }

  function onDoubleClick(event: { clientX: number; clientY: number }) {
    if (view.scale > MIN_SCALE) reset();
    else zoomTo(DOUBLE_ZOOM, fromCentre(event.clientX, event.clientY));
  }

  // Any key code counts as well as the letter, so the Persian layout (R is «ق») works too.
  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const { key, code } = event;
    const onStage = event.target === stage.current;
    if (key === '+' || key === '=' || code === 'NumpadAdd' || code === 'Equal')
      step(1);
    else if (
      key === '-' ||
      key === '_' ||
      code === 'NumpadSubtract' ||
      code === 'Minus'
    )
      step(-1);
    else if (key === '0' || code === 'Digit0' || code === 'Numpad0') reset();
    else if (key.toLowerCase() === 'r' || code === 'KeyR') rotate();
    else if (onStage && key === 'ArrowLeft') panBy(PAN_STEP, 0);
    else if (onStage && key === 'ArrowRight') panBy(-PAN_STEP, 0);
    else if (onStage && key === 'ArrowUp') panBy(0, PAN_STEP);
    else if (onStage && key === 'ArrowDown') panBy(0, -PAN_STEP);
    else return;
    event.preventDefault();
  }

  return {
    view,
    gesturing,
    stage,
    image,
    zoomIn: () => step(1),
    zoomOut: () => step(-1),
    rotate,
    reset,
    canZoomIn: view.scale < MAX_SCALE,
    canZoomOut: view.scale > MIN_SCALE,
    onKeyDown,
    stageProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: onPointerEnd,
      onPointerCancel: onPointerEnd,
      onDoubleClick,
    },
  };
}
