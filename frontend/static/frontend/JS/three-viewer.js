/**
 * VH Three.js GLB Viewer
 * Replaces <model-viewer> with a direct Three.js WebGL renderer.
 * Supports: auto-rotate, orbit controls, auto-fit, responsive resize, disposal.
 */
import * as THREE from 'three';
import { GLTFLoader }    from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function initViewer(container, modelPath, { onLoad, onError } = {}) {
    if (!container || !modelPath) return null;

    // ── Scene ───────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);

    // ── Camera ──────────────────────────────────────────────────────
    const camera = new THREE.PerspectiveCamera(
        40,
        container.clientWidth / container.clientHeight,
        0.01, 1000
    );

    // ── Renderer ────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // cap at 2x for perf
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;border-radius:inherit;';
    container.appendChild(renderer.domElement);

    // ── Lighting ────────────────────────────────────────────────────
    // Hemisphere: warm sky, cool ground — natural ambient
    const hemi = new THREE.HemisphereLight(0xffeedd, 0x334466, 0.8);
    scene.add(hemi);

    // Key light (upper-right)
    const key = new THREE.DirectionalLight(0xffffff, 2);
    key.position.set(4, 8, 5);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 0.1;
    key.shadow.camera.far = 50;
    scene.add(key);

    // Fill light (left side, softer)
    const fill = new THREE.DirectionalLight(0xcce8ff, 0.6);
    fill.position.set(-4, 2, -3);
    scene.add(fill);

    // Rim light (back, gives edge definition)
    const rim = new THREE.DirectionalLight(0xffffff, 0.4);
    rim.position.set(0, -2, -6);
    scene.add(rim);

    // ── Controls ────────────────────────────────────────────────────
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping    = true;
    controls.dampingFactor    = 0.06;
    controls.autoRotate       = true;
    controls.autoRotateSpeed  = 1.2;
    controls.enablePan        = false;
    controls.minDistance      = 0.5;
    controls.maxDistance      = 20;
    controls.maxPolarAngle    = Math.PI * 0.85; // don't flip upside-down
    controls.addEventListener('start', () => { controls.autoRotate = false; });

    // ── Load model ──────────────────────────────────────────────────
    const loader = new GLTFLoader();
    loader.load(
        modelPath,
        (gltf) => {
            const model = gltf.scene;

            // Enable shadows on every mesh
            model.traverse(node => {
                if (node.isMesh) {
                    node.castShadow    = true;
                    node.receiveShadow = true;
                }
            });

            // Auto-fit: centre model and place camera at a comfortable distance
            const box    = new THREE.Box3().setFromObject(model);
            const centre = box.getCenter(new THREE.Vector3());
            const size   = box.getSize(new THREE.Vector3());
            const span   = Math.max(size.x, size.y, size.z);

            model.position.sub(centre);            // centre at origin
            camera.position.set(0, span * 0.4, span * 2.2);
            camera.near = span * 0.01;
            camera.far  = span * 100;
            camera.updateProjectionMatrix();

            controls.target.set(0, 0, 0);
            controls.minDistance = span * 0.8;
            controls.maxDistance = span * 6;
            controls.update();

            scene.add(model);
            onLoad?.();
        },
        undefined,
        (err) => {
            console.error('[three-viewer] load error:', err);
            onError?.();
        }
    );

    // ── Ground shadow plane ─────────────────────────────────────────
    const ground = new THREE.Mesh(
        new THREE.PlaneGeometry(40, 40),
        new THREE.ShadowMaterial({ opacity: 0.12 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.001;
    ground.receiveShadow = true;
    scene.add(ground);

    // ── Animation loop ──────────────────────────────────────────────
    let animId;
    function animate() {
        animId = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    // ── Responsive resize ───────────────────────────────────────────
    const ro = new ResizeObserver(() => {
        const w = container.clientWidth;
        const h = container.clientHeight;
        if (!w || !h) return;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    });
    ro.observe(container);

    // ── Disposal ────────────────────────────────────────────────────
    return {
        dispose() {
            cancelAnimationFrame(animId);
            ro.disconnect();
            controls.dispose();
            renderer.dispose();
            renderer.domElement.remove();
        },
        pauseRotation()  { controls.autoRotate = false; },
        resumeRotation() { controls.autoRotate = true; },
    };
}
