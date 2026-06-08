// ASIKO Boutique — Simplified Try-On 3D Engine
// Purpose: Load an avatar GLB + load a clothing GLB on top. That's it.
// No parametric mannequins, no capsule layers, no procedural geometry.
// Just: pick garment → see it on avatar → swap → pay.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// ── Avatar paths (single source of truth) ──────────────────────
const AVATAR_ASSETS = {
    male:   '/static/models/avatar_male.glb',
    female: '/static/models/avatar_female.glb',
};

// ── Default camera positions ───────────────────────────────────
const DEFAULT_CAM = new THREE.Vector3(0, 1.2, 3.2);
const DEFAULT_TARGET = new THREE.Vector3(0, 0.9, 0);

class TryOnEngine {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.composer = null;
        this.gltfLoader = new GLTFLoader();

        // Avatar state
        this.currentAvatar = null;     // THREE.Group wrapper
        this.currentAvatarMesh = null; // raw loaded GLTF scene

        // Garment state
        this.currentGarment = null;    // THREE.Group wrapper
        this.currentGarmentMesh = null;

        // Environment
        this.pedestal = null;
        this.hemi = null;
        this.key = null;

        // Render loop
        this._loopRunning = false;
        this._loadRequestId = 0;

        this._initScene();
        this._startLoop();
    }

    // ── Scene setup ────────────────────────────────────────────
    _initScene() {
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
        });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xfbf9f6);

        // Camera
        this.camera = new THREE.PerspectiveCamera(35, w / h, 0.1, 100);
        this.camera.position.copy(DEFAULT_CAM);

        // Environment map for PBR IBL
        const pmremGen = new THREE.PMREMGenerator(this.renderer);
        pmremGen.compileEquirectangularShader();
        const envTex = pmremGen.fromScene(new RoomEnvironment(), 0.04).texture;
        this.scene.environment = envTex;
        pmremGen.dispose();

        // Post-processing: subtle bloom
        this.composer = new EffectComposer(this.renderer);
        this.composer.addPass(new RenderPass(this.scene, this.camera));
        const bloom = new UnrealBloomPass(
            new THREE.Vector2(w, h),
            0.18,   // strength — subtle glow
            0.92,   // radius
            0.85    // threshold
        );
        this.composer.addPass(bloom);
        this.composer.addPass(new OutputPass());

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.target.copy(DEFAULT_TARGET);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.minDistance = 1.5;
        this.controls.maxDistance = 6;
        this.controls.maxPolarAngle = Math.PI * 0.85;
        this.controls.autoRotate = false;
        this.controls.update();

        // Lighting
        this._initLighting();

        // Environment props
        this._initEnvironment();

        // Resize handler
        this._onResize = () => {
            const w2 = this.container.clientWidth;
            const h2 = this.container.clientHeight;
            this.camera.aspect = w2 / h2;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(w2, h2);
            this.composer.setSize(w2, h2);
        };
        window.addEventListener('resize', this._onResize);
        if (typeof ResizeObserver !== 'undefined') {
            this._resizeObs = new ResizeObserver(this._onResize);
            this._resizeObs.observe(this.container);
        }
    }

    _initLighting() {
        // Hemisphere light — soft ambient
        this.hemi = new THREE.HemisphereLight(0xfbf9f6, 0x0d2a22, 0.6);
        this.scene.add(this.hemi);

        // Key light — warm directional
        this.key = new THREE.DirectionalLight(0xfff4e6, 1.2);
        this.key.position.set(3, 5, 4);
        this.key.castShadow = true;
        this.key.shadow.mapSize.set(1024, 1024);
        this.key.shadow.camera.near = 0.5;
        this.key.shadow.camera.far = 20;
        this.key.shadow.camera.left = -3;
        this.key.shadow.camera.right = 3;
        this.key.shadow.camera.top = 3;
        this.key.shadow.camera.bottom = -1;
        this.key.shadow.bias = -0.001;
        this.scene.add(this.key);

        // Rim light — gold accent
        const rim = new THREE.DirectionalLight(0xd4af37, 0.3);
        rim.position.set(-2, 3, -3);
        this.scene.add(rim);
    }

    _initEnvironment() {
        // Pedestal — simple cylinder
        const pedGeo = new THREE.CylinderGeometry(0.6, 0.65, 0.08, 64);
        const pedMat = new THREE.MeshStandardMaterial({
            color: 0x0d2a22,
            roughness: 0.4,
            metalness: 0.1,
        });
        this.pedestal = new THREE.Mesh(pedGeo, pedMat);
        this.pedestal.position.y = 0.04;
        this.pedestal.receiveShadow = true;
        this.scene.add(this.pedestal);

        // Gold ring on pedestal
        const ringGeo = new THREE.TorusGeometry(0.62, 0.008, 16, 64);
        const ringMat = new THREE.MeshStandardMaterial({
            color: 0xd4af37,
            roughness: 0.3,
            metalness: 0.7,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.085;
        this.scene.add(ring);

        // Floor plane
        const floorGeo = new THREE.PlaneGeometry(20, 20);
        const floorMat = new THREE.MeshStandardMaterial({
            color: 0xfbf9f6,
            roughness: 0.9,
            metalness: 0,
        });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = 0;
        floor.receiveShadow = true;
        this.scene.add(floor);
    }

    // ── Avatar loading ─────────────────────────────────────────
    loadAvatar(gender = 'female') {
        const path = AVATAR_ASSETS[gender];
        if (!path) {
            console.warn(`[TryOnEngine] No avatar path for gender: ${gender}`);
            return Promise.resolve(null);
        }
        return this._loadAvatarGLB(path);
    }

    async _loadAvatarGLB(url) {
        this._purgeAvatar();
        const reqId = ++this._loadRequestId;

        try {
            const gltf = await this.gltfLoader.loadAsync(url);
            if (reqId !== this._loadRequestId) return null; // stale

            const group = new THREE.Group();
            group.name = 'avatar-wrapper';
            group.add(gltf.scene);

            // Fit to viewport
            this._fitToViewport(gltf.scene, true);

            // Apply realism shader to avatar surfaces
            this._applyRealismShader(gltf.scene);

            // Enable shadows
            gltf.scene.traverse((child) => {
                if (child.isMesh) {
                    child.castShadow = true;
                    child.receiveShadow = true;
                }
            });

            this.scene.add(group);
            this.currentAvatar = group;
            this.currentAvatarMesh = gltf.scene;

            // Position garment relative to avatar if one is already loaded
            if (this.currentGarment) {
                this._positionGarmentOnAvatar();
            }

            return group;
        } catch (err) {
            console.error('[TryOnEngine] Avatar load failed:', err);
            return null;
        }
    }

    _purgeAvatar() {
        if (this.currentAvatarMesh) {
            this._disposeNode(this.currentAvatarMesh);
            this.currentAvatarMesh = null;
        }
        if (this.currentAvatar) {
            this.scene.remove(this.currentAvatar);
            this.currentAvatar = null;
        }
    }

    // ── Garment loading ────────────────────────────────────────
    async loadGarment(glbUrl) {
        this._purgeGarment();
        const reqId = ++this._loadRequestId;

        try {
            const gltf = await this.gltfLoader.loadAsync(glbUrl);
            if (reqId !== this._loadRequestId) return null;

            const group = new THREE.Group();
            group.name = 'garment-wrapper';
            group.add(gltf.scene);

            // Fit garment to roughly match avatar scale
            this._fitToViewport(gltf.scene, false);

            // Enable double-sided rendering for clothing
            gltf.scene.traverse((child) => {
                if (child.isMesh) {
                    child.castShadow = true;
                    child.receiveShadow = true;
                    if (child.material) {
                        child.material.side = THREE.DoubleSide;
                    }
                }
            });

            this.scene.add(group);
            this.currentGarment = group;
            this.currentGarmentMesh = gltf.scene;

            // Position garment on avatar if avatar exists
            if (this.currentAvatar) {
                this._positionGarmentOnAvatar();
            }

            return group;
        } catch (err) {
            console.error('[TryOnEngine] Garment load failed:', err);
            return null;
        }
    }

    _purgeGarment() {
        if (this.currentGarmentMesh) {
            this._disposeNode(this.currentGarmentMesh);
            this.currentGarmentMesh = null;
        }
        if (this.currentGarment) {
            this.scene.remove(this.currentGarment);
            this.currentGarment = null;
        }
    }

    clearGarment() {
        this._purgeGarment();
    }

    _positionGarmentOnAvatar() {
        if (!this.currentAvatar || !this.currentGarment) return;

        // Match garment position to avatar center
        const avatarBox = new THREE.Box3().setFromObject(this.currentAvatar);
        const garmentBox = new THREE.Box3().setFromObject(this.currentGarment);

        const avatarCenter = avatarBox.getCenter(new THREE.Vector3());
        const garmentCenter = garmentBox.getCenter(new THREE.Vector3());

        // Offset garment so its center aligns with avatar center
        this.currentGarment.position.x += avatarCenter.x - garmentCenter.x;
        this.currentGarment.position.z += avatarCenter.z - garmentCenter.z;

        // Align bottom of garment with bottom of avatar
        const avatarBottom = avatarBox.min.y;
        const garmentBottom = garmentBox.min.y;
        this.currentGarment.position.y += avatarBottom - garmentBottom;
    }

    // ── Fit model to viewport ──────────────────────────────────
    _fitToViewport(model, isAvatar) {
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());

        // Target height: avatar ~1.6 units, garment ~1.4 units
        const targetHeight = isAvatar ? 1.6 : 1.4;
        const scale = targetHeight / size.y;

        model.scale.setScalar(scale);

        // Recompute after scaling
        box.setFromObject(model);
        box.getCenter(center);

        // Center horizontally, lift so feet touch pedestal
        model.position.x -= center.x;
        model.position.z -= center.z;
        model.position.y -= box.min.y;

        // Lift slightly above pedestal
        if (isAvatar) {
            model.position.y += 0.08;
        }
    }

    // ── Realism shader for avatar surfaces ─────────────────────
    _applyRealismShader(root) {
        const SKIN_PATTERN = /skin|head|face|hand|arm|neck|body|torso|leg|foot|feet/i;
        const HAIR_PATTERN = /hair|brow|lash/i;
        const EYE_PATTERN = /eye|iris|pupil/i;

        root.traverse((child) => {
            if (!child.isMesh || !child.material) return;

            const name = child.name || '';
            const mat = child.material;

            if (EYE_PATTERN.test(name)) {
                // Eyes: glossy
                mat.roughness = 0.05;
                mat.metalness = 0;
            } else if (HAIR_PATTERN.test(name)) {
                // Hair: slightly glossy
                mat.roughness = 0.6;
                mat.metalness = 0.05;
            } else if (SKIN_PATTERN.test(name)) {
                // Skin: subsurface approximation via transmission
                mat.roughness = 0.55;
                mat.metalness = 0;
                mat.wireframe = false;
                // Warm skin tint
                if (mat.color) {
                    const hsl = {};
                    mat.color.getHSL(hsl);
                    mat.color.setHSL(
                        hsl.h + 0.01,
                        Math.min(hsl.s + 0.05, 1),
                        Math.min(hsl.l + 0.02, 1)
                    );
                }
            } else {
                // Default (clothing, accessories)
                mat.roughness = Math.max(mat.roughness || 0.5, 0.3);
                mat.metalness = Math.min(mat.metalness || 0, 0.1);
            }

            mat.needsUpdate = true;
        });
    }

    // ── Disposal ───────────────────────────────────────────────
    _disposeNode(node) {
        if (!node) return;
        node.traverse((child) => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach((m) => this._disposeMaterial(m));
                } else {
                    this._disposeMaterial(child.material);
                }
            }
        });
    }

    _disposeMaterial(mat) {
        if (!mat) return;
        const keys = [
            'map', 'normalMap', 'roughnessMap', 'metalnessMap',
            'emissiveMap', 'aoMap', 'envMap', 'alphaMap',
            'bumpMap', 'displacementMap', 'lightMap',
        ];
        keys.forEach((k) => {
            if (mat[k]) mat[k].dispose();
        });
        mat.dispose();
    }

    // ── Camera controls ────────────────────────────────────────
    zoomIn() {
        this._zoomBy(0.85);
    }

    zoomOut() {
        this._zoomBy(1.15);
    }

    _zoomBy(factor) {
        const dir = new THREE.Vector3()
            .subVectors(this.camera.position, this.controls.target);
        const len = dir.length();
        const newLen = Math.max(1.0, Math.min(6, len * factor));
        dir.normalize().multiplyScalar(newLen);
        this.camera.position.copy(this.controls.target).add(dir);
    }

    resetView() {
        this.camera.position.copy(DEFAULT_CAM);
        this.controls.target.copy(DEFAULT_TARGET);
        this.controls.update();
    }

    // ── Render loop ────────────────────────────────────────────
    _startLoop() {
        if (this._loopRunning) return;
        this._loopRunning = true;

        const animate = () => {
            if (!this._loopRunning) return;
            requestAnimationFrame(animate);

            try {
                this.controls.update();
                this.composer.render();
            } catch (err) {
                console.warn('[TryOnEngine] Render error:', err);
            }
        };

        requestAnimationFrame(animate);
    }

    // ── Cleanup ────────────────────────────────────────────────
    dispose() {
        this._loopRunning = false;
        window.removeEventListener('resize', this._onResize);
        if (this._resizeObs) this._resizeObs.disconnect();

        this._purgeAvatar();
        this._purgeGarment();

        if (this.composer) {
            this.composer.dispose();
        }
        if (this.renderer) {
            this.renderer.dispose();
            this.renderer.domElement.remove();
        }

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.composer = null;
    }
}

// ── Public entry point ────────────────────────────────────────
export function initTryOnEngine(container) {
    return new TryOnEngine(container);
}

// Backward compatibility alias
export function initAtelierEngine(container) {
    return new TryOnEngine(container);
}
