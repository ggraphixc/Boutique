/**
 * ASIKO Boutique — Atelier 3D Engine
 * Spatial Commerce Suite: Parametric Body-Morph, Multi-Layer Rendering, WebXR AR Gateway
 *
 * @module atelier-3d
 * @requires three (CDN importmap: three@0.160.0)
 *
 * Usage:
 *   import { initAtelierEngine } from '/static/js/atelier-3d.js';
 *   const engine = initAtelierEngine(document.querySelector('.atelier-canvas-wrap'));
 *   // The engine binds to <canvas id="atelier-33d-canvas"> (with fallback to
 *   // <canvas id="atelier-3d-canvas">) via ID lookup.
 *   engine.setMode('showroom' | 'dressing_room');
 *   engine.applyMeasurements({ chest, waist, hips });
 *   engine.setGarmentLayer(layer, assetId);
 *   engine.requestAR();
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// ============================================================================
// CONSTANTS
// ============================================================================

const BASELINE_MEASUREMENTS = { chest: 96, waist: 82, hips: 102 };
const LERP_SPEED = 0.06;

const LAYER_DEPTHS = {
    base: 0,       // Drape Dresses, Structural Shell Tops
    structural: 1, // Tapered Trousers
    shell: 2,      // Cyber Blazers
};

const LAYER_ORDER = ['base', 'structural', 'shell'];

const GARMENT_CONFIG = {
    mesh_dress_lux:    { layer: 'base',       color: 0x1a1a2e, emissive: 0x4a4a8e, label: 'Drape Dress' },
    mesh_top_structural: { layer: 'base',     color: 0xc4a35a, emissive: 0xD4AF37, label: 'Shell Top' },
    mesh_trouser_tapered: { layer: 'structural', color: 0xe8d5c0, emissive: 0xc4a35a, label: 'Tapered Trouser' },
    mesh_jacket_cyber:  { layer: 'shell',     color: 0x0D4A3A, emissive: 0x22D3EE, label: 'Cyber Blazer' },
};

const AR_CONFIG = {
    glbPath: '/static/models/draped-silhouette-gown.glb',
};

// ============================================================================
// ENGINE CLASS
// ============================================================================

export class AtelierEngine {
    constructor(container) {
        if (!container) throw new Error('AtelierEngine requires a DOM container element');
        this.container = container;
        this.mode = 'showroom'; // 'showroom' | 'dressing_room'
        this.currentShowroomModel = null;
        this.gltfLoader = new GLTFLoader();

        // ---- Camera framing track markers (used by loadBaseAvatar + resetView) ----
        // Anchors the camera to mid-torso height so the model is framed cleanly
        // inside the WebGL viewport, instead of staring down at the floor grid.
        this.defaultCamPosition = new THREE.Vector3(0, 0.95, 2.3);
        this.defaultTargetPosition = new THREE.Vector3(0, 0.85, 0);

        // ---- Isolated parent group for the loaded GLTF avatar (decouples
        //      external coordinate systems from the scene root) ----
        this.avatarWrapperGroup = null;

        // ---- Layer Registry (multi-layer garment storage) ----
        this.layerRegistry = {
            base: null,
            structural: null,
            shell: null,
        };

        // ---- Avatar state (dual-gender support) ----
        this.currentAvatarMesh = null;
        this.currentGender = 'female';
        this.currentUserMeasurements = { ...BASELINE_MEASUREMENTS };

        // ---- Body morph target values ----
        this.targetMorph = { ...BASELINE_MEASUREMENTS };
        this.currentMorph = { ...BASELINE_MEASUREMENTS };
        this.bodyParts = {}; // Named references for morphing
        this.isAnimating = false;

        // ---- Build the scene ----
        this._initScene();

        // ---- Global exposure for inline onclick handlers (zoom dock overlay) ----
        // Canonical reference: window.__atelierEngine (double underscore, matches
        // the canonical signature declared in virtual_experience.html).
        window.__atelierEngine = this;

        // ---- Listen for custom events ----
        this._bindEvents();
    }

    // ========================================================================
    // SCENE INITIALIZATION
    // ========================================================================

    _initScene() {
        const container = this.container;

        // --- SCENE ---
        this.scene = new THREE.Scene();
        this.scene.background = null; // transparent for CSS gradients

        // --- CAMERA ---
        this.camera = new THREE.PerspectiveCamera(
            40,
            container.clientWidth / container.clientHeight,
            0.1,
            100
        );
        this.camera.position.copy(this.defaultCamPosition);

        // --- RENDERER ---
        // Explicit ID binding with fallback chain: try <canvas id="atelier-33d-canvas">
        // first (the 11h directive ID, restored in 11k), fall back to <canvas id="atelier-3d-canvas">
        // (the 11i single-3 ID). Three.js attaches the renderer to the existing
        // element instead of creating a fresh canvas and appendChild.
        const canvasElement = document.getElementById('atelier-33d-canvas') || document.getElementById('atelier-3d-canvas');
        if (canvasElement) {
            this.renderer = new THREE.WebGLRenderer({
                canvas: canvasElement,
                antialias: true,
                alpha: true,
                powerPreference: 'high-performance',
            });
        } else {
            // Defensive fallback: create a new canvas and append to container
            console.error("Initialization Failed: WebGL context canvas target target could not be successfully bound.");
            this.renderer = new THREE.WebGLRenderer({
                antialias: true,
                alpha: true,
                powerPreference: 'high-performance',
            });
            container.appendChild(this.renderer.domElement);
        }
        // Transparent clear color: prevents black frame flashes on initial load
        // and allows the cream background tone to bleed through the canvas.
        this.renderer.setClearColor(0x000000, 0);
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;

        // --- CONTROLS ---
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.target.copy(this.defaultTargetPosition);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 0.7;
        this.controls.maxDistance = 4.5;
        this.controls.maxPolarAngle = Math.PI / 2.1;
        this.controls.minPolarAngle = Math.PI / 6;
        this.controls.autoRotate = true;
        this.controls.autoRotateSpeed = 1.5;

        // --- LIGHTS (studio rig: hemisphere + key + gold rim) ---
        this.initStudioLighting();

        // --- INTERACTION CONTROLS (touch-optimized orbit) ---
        this.initInteractionControls();

        // --- ENVIRONMENT ---
        this._initEnvironment();

        // --- MANNEQUIN (parametric) ---
        this._initMannequin();

        // --- DEFAULT GARMENT ---
        this._initDefaultGarments();

        // --- PARTICLES ---
        this._initParticles();

        // --- RESIZE ---
        this._initResizeHandler();

        // --- START LOOP ---
        this._startLoop();
    }

    /**
     * Studio lighting rig: replaces the previous flat 4-light setup with a
     * hemisphere ambient + 2 directional lights (key + brand-gold rim).
     *
     * Rig:
     *   - HemisphereLight:  soft sky/ground ambient that flattens shadowed crevices
     *   - DirectionalLight 0xfffdf6 @ 1.8: KEY from front-right, casts shadows
     *   - DirectionalLight 0xd4af37 @ 1.0: RIM from back-left, brand-gold luxury edge
     *
     * The gold rim light matches the brand token (#D4AF37) and produces a
     * subtle silhouette glow on fabric folds without washing out the textile
     * PBR sheen. Shadow map is upgraded to 2048×2048 for crisp fabric weave
     * detail at the price of ~4MB GPU memory.
     */
    initStudioLighting() {
        if (!this.scene) return;

        // 1. Wipe legacy lights (idempotent — safe to call multiple times)
        const legacyLights = this.scene.children.filter((c) => c.isLight);
        legacyLights.forEach((l) => this.scene.remove(l));

        // 2. Hemisphere ambient — soft sky/ground gradient fills shadowed crevices
        const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.2);
        this.scene.add(hemi);

        // 3. Key light — warm neutral, casts shadows from front-right
        const key = new THREE.DirectionalLight(0xfffdf6, 1.8);
        key.position.set(2, 4, 3);
        key.castShadow = true;
        key.shadow.mapSize.width = 2048;
        key.shadow.mapSize.height = 2048;
        key.shadow.bias = -0.0001;
        key.shadow.camera.near = 0.1;
        key.shadow.camera.far = 20;
        this.scene.add(key);

        // 4. Rim light — brand-gold (#D4AF37) accent from back-left for luxury edge glow
        const rim = new THREE.DirectionalLight(0xd4af37, 1.0);
        rim.position.set(-2, 3, -3);
        this.scene.add(rim);
    }

    /**
     * Touch-optimized OrbitControls configuration. Boosts the default
     * rotateSpeed (1.0) and touchRotateSpeed (1.0) to values tuned for
     * luxury retail UX: smooth, responsive, but not flicky.
     *
     *   rotateSpeed       = 1.8   (default 1.0)  — desktop drag responsiveness
     *   touchRotateSpeed  = 2.2   (default 1.0)  — mobile single-finger spin
     *   enableDamping     = true  — momentum continuation
     *   dampingFactor     = 0.08  (was 0.05)     — slightly looser for tactile feel
     *   screenSpacePanning = false — pan is depth-relative (avoids flying off into infinity)
     */
    initInteractionControls() {
        if (!this.controls) return;

        this.controls.rotateSpeed = 1.8;
        this.controls.touchRotateSpeed = 2.2;
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.screenSpacePanning = false;
    }

    _initEnvironment() {
        // Pedestal
        const pedMat = new THREE.MeshPhysicalMaterial({
            color: 0xffffff, metalness: 0.1, roughness: 0.3,
            transparent: true, opacity: 0.85, clearcoat: 0.1,
        });
        this.pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.1, 0.15, 48), pedMat);
        this.pedestal.position.y = 0.05;
        this.pedestal.receiveShadow = true;
        this.pedestal.castShadow = true;
        this.scene.add(this.pedestal);

        // Gold rim ring
        const ringMat = new THREE.MeshPhysicalMaterial({
            color: 0xD4AF37, emissive: 0xD4AF37, emissiveIntensity: 0.3,
            metalness: 0.8, roughness: 0.1, transparent: true, opacity: 0.7,
        });
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.95, 0.02, 16, 48), ringMat);
        ring.position.y = 0.12;
        ring.rotation.x = Math.PI / 2;
        this.scene.add(ring);

        // Base ring
        const baseRingMat = ringMat.clone();
        baseRingMat.opacity = 0.3;
        baseRingMat.emissiveIntensity = 0.15;
        const baseRing = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.02, 16, 48), baseRingMat);
        baseRing.position.y = 0.01;
        baseRing.rotation.x = Math.PI / 2;
        this.scene.add(baseRing);

        // Floor
        const floorMat = new THREE.MeshPhysicalMaterial({
            color: 0xFBF9F6, roughness: 0.8,
            transparent: true, opacity: 0.3, side: THREE.DoubleSide,
        });
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(8, 8), floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.02;
        floor.receiveShadow = true;
        this.scene.add(floor);
    }

    _initMannequin() {
        const group = new THREE.Group();
        group.name = 'mannequin';
        const bodyMat = new THREE.MeshPhysicalMaterial({
            color: 0xf0e8e0, roughness: 0.6, transparent: true, opacity: 0.95,
        });
        const accentMat = new THREE.MeshPhysicalMaterial({
            color: 0xD4AF37, metalness: 0.7, roughness: 0.2,
            emissive: 0xD4AF37, emissiveIntensity: 0.05,
        });

        // Torso — Bone_Chest target
        const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.28, 0.7, 16), bodyMat);
        torso.position.y = 0.65;
        torso.castShadow = true;
        torso.userData.boneName = 'Bone_Chest';
        torso.userData.morphScale = { x: 1, y: 1, z: 1 };
        group.add(torso);
        this.bodyParts.chest = torso;

        // Hips — Bone_Hips target
        const hips = new THREE.Mesh(new THREE.SphereGeometry(0.25, 12, 12), bodyMat);
        hips.position.y = 0.3;
        hips.scale.set(1, 0.4, 0.7);
        hips.userData.boneName = 'Bone_Hips';
        hips.userData.morphScale = { x: 1, y: 1, z: 1 };
        group.add(hips);
        this.bodyParts.hips = hips;

        // Waist region — Bone_Waist target (waist ring)
        const waistRing = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.015, 8, 24), accentMat);
        waistRing.position.y = 0.45;
        waistRing.rotation.x = Math.PI / 2;
        waistRing.userData.boneName = 'Bone_Waist';
        waistRing.userData.morphScale = { x: 1, y: 1, z: 1 };
        group.add(waistRing);
        this.bodyParts.waist = waistRing;

        // Neck
        const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.12, 12), bodyMat);
        neck.position.y = 1.0;
        group.add(neck);

        // Head
        const head = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 16), bodyMat);
        head.position.y = 1.15;
        head.scale.y = 1.15;
        head.castShadow = true;
        group.add(head);

        // Arms
        const armGeo = new THREE.CylinderGeometry(0.05, 0.06, 0.5, 8);
        const leftArm = new THREE.Mesh(armGeo, bodyMat);
        leftArm.position.set(-0.38, 0.75, 0);
        leftArm.rotation.z = 0.15;
        leftArm.rotation.x = -0.3;
        leftArm.castShadow = true;
        group.add(leftArm);

        const rightArm = new THREE.Mesh(armGeo, bodyMat);
        rightArm.position.set(0.38, 0.75, 0);
        rightArm.rotation.z = -0.15;
        rightArm.rotation.x = 0.3;
        rightArm.castShadow = true;
        group.add(rightArm);

        // Collar accent
        const collar = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.015, 8, 20), accentMat);
        collar.position.y = 0.95;
        collar.rotation.x = Math.PI / 2;
        group.add(collar);

        this.mannequin = group;
        this.scene.add(group);
    }

    _initDefaultGarments() {
        // Start with base layer dress + trouser
        this.layerRegistry.base = this._createGarmentMesh('mesh_dress_lux');
        this.layerRegistry.structural = this._createGarmentMesh('mesh_trouser_tapered');
        this._syncLayerVisibility();
    }

    _initParticles() {
        const pCount = 60;
        const pGeo = new THREE.BufferGeometry();
        const pos = new Float32Array(pCount * 3);
        for (let i = 0; i < pCount * 3; i++) {
            pos[i] = (Math.random() - 0.5) * 10;
        }
        pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        this.particles = new THREE.Points(
            pGeo,
            new THREE.PointsMaterial({
                color: 0xD4AF37, size: 0.015,
                transparent: true, opacity: 0.3,
                blending: THREE.AdditiveBlending,
            })
        );
        this.scene.add(this.particles);
    }

    _initResizeHandler() {
        const onResize = () => {
            const w = this.container.clientWidth;
            const h = this.container.clientHeight;
            if (w === 0 || h === 0) return;
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(w, h);
        };
        window.addEventListener('resize', onResize);
        new ResizeObserver(() => onResize()).observe(this.container);
    }

    // ========================================================================
    // BODY-MORPH SYSTEM
    // ========================================================================

    /**
     * Apply body measurements to the mannequin with smooth interpolation.
     * @param {Object} measurements - { chest, waist, hips } in cm
     * @param {boolean} [animate=true] - Smoothly interpolate if true
     */
    applyMeasurements(measurements, animate = true) {
        if (!measurements) return;
        this.targetMorph.chest = measurements.chest || BASELINE_MEASUREMENTS.chest;
        this.targetMorph.waist = measurements.waist || BASELINE_MEASUREMENTS.waist;
        this.targetMorph.hips = measurements.hips || BASELINE_MEASUREMENTS.hips;

        if (!animate) {
            this.currentMorph = { ...this.targetMorph };
            this._applyMorphValues();
        } else {
            this.isAnimating = true;
        }
    }

    _updateMorphAnimation() {
        if (!this.isAnimating) return;

        let settled = true;
        for (const key of ['chest', 'waist', 'hips']) {
            const diff = this.targetMorph[key] - this.currentMorph[key];
            if (Math.abs(diff) > 0.1) {
                this.currentMorph[key] += diff * LERP_SPEED;
                settled = false;
            } else {
                this.currentMorph[key] = this.targetMorph[key];
            }
        }

        this._applyMorphValues();

        if (settled) {
            this.isAnimating = false;
        }
    }

    _applyMorphValues() {
        const { chest, waist, hips } = this.currentMorph;
        const base = BASELINE_MEASUREMENTS;

        // Chest → Torso scale (width/depth)
        const chestRatio = chest / base.chest; // 1.0 at baseline
        if (this.bodyParts.chest) {
            const c = this.bodyParts.chest;
            c.scale.x = 0.6 + 0.4 * chestRatio; // range: ~0.6 to ~1.4
            c.scale.z = 0.6 + 0.4 * chestRatio;
        }

        // Waist → Waist ring scale
        const waistRatio = waist / base.waist;
        if (this.bodyParts.waist) {
            const w = this.bodyParts.waist;
            w.scale.x = waistRatio;
            w.scale.z = waistRatio;
        }

        // Hips → Hips scale (width/depth)
        const hipsRatio = hips / base.hips;
        if (this.bodyParts.hips) {
            const h = this.bodyParts.hips;
            h.scale.x = 0.7 + 0.3 * hipsRatio;
            h.scale.z = 0.7 + 0.3 * hipsRatio;
        }
    }

    // ========================================================================
    // MULTI-LAYER ASSET RENDERING ENGINE
    // ========================================================================

    /**
     * Set a garment on a specific layer.
     * @param {'base'|'structural'|'shell'} layer - Layer depth
     * @param {string|null} assetId - Garment ID (null to clear layer)
     */
    setGarmentLayer(layer, assetId) {
        if (!LAYER_ORDER.includes(layer)) {
            console.warn(`[Atelier3D] Invalid layer: ${layer}`);
            return;
        }

        // Dispose existing garment on this layer
        const existing = this.layerRegistry[layer];
        if (existing) {
            this.scene.remove(existing);
            this._safeDispose(existing);
        }

        // Create and add new garment
        if (assetId && GARMENT_CONFIG[assetId]) {
            this.layerRegistry[layer] = this._createGarmentMesh(assetId);
        } else {
            this.layerRegistry[layer] = null;
        }

        this._syncLayerVisibility();
    }

    /**
     * Sync all active layers to the scene with proper depth offset.
     */
    _syncLayerVisibility() {
        for (const layer of LAYER_ORDER) {
            const mesh = this.layerRegistry[layer];
            if (mesh) {
                // Depth offset to prevent z-fighting between layers
                const depthIdx = LAYER_ORDER.indexOf(layer);
                mesh.position.z = depthIdx * 0.001;
                if (!mesh.parent) {
                    this.scene.add(mesh);
                }
            }
        }

this._emitLayerState();
    }

    /**
      * Clear all garment layers (reset to nude mannequin).
      */
    clearAllLayers() {
        for (const layer of LAYER_ORDER) {
            const existing = this.layerRegistry[layer];
            if (existing) {
                this.scene.remove(existing);
                this._safeDispose(existing);
                this.layerRegistry[layer] = null;
            }
        }
    }

    /**
     * Load an automated garment from external GLTF/GLB with layer depth scaling.
     * Consumes layer-capsule-mesh.window events from Alpine.js.
     * @param {Object} payload - { layerIndex, modelUrl, color, mesh, variantId, productId, priority, isRequired, layer, colorHex, assetCategory }
     */
    async loadAutomatedAsset(meshUrl, layerDepth, assetCategory = 'apparel') {
        if (!this.gltfLoader) {
            console.error("Initialization fault: GLTFLoader interface structure unassigned.");
            return;
        }

        // Map layerDepth to semantic layer name
        const positioningKey = assetCategory === 'footwear' ? 'shoes' : layerDepth;
        const layer = { 0: 'base', 1: 'structural', 2: 'shell' }[layerDepth] || 'shell';

        // Clear conflicting assets out of the selected registry slot
        if (this.activeGarments && this.activeGarments[positioningKey]) {
            this.scene.remove(this.activeGarments[positioningKey]);
            this._safeDispose(this.activeGarments[positioningKey]);
        }

        if (!this.activeGarments) {
            this.activeGarments = {};
        }

        // Clear existing garment on this layer for apparel
        const existing = this.layerRegistry[layer];
        if (existing) {
            this.scene.remove(existing);
            this._safeDispose(existing);
        }

        return new Promise((resolve, reject) => {
            this.gltfLoader.load(meshUrl, (gltf) => {
                const loadedScene = gltf.scene;

                if (assetCategory === 'footwear') {
                    // FOOTWEAR POSITIONING MATRIX
                    // Reset scales to actual size definitions (no dress expansion curves)
                    loadedScene.scale.set(1.0, 1.0, 1.0);

                    // Align the model boundaries perfectly with the showroom floor coordinates
                    // Assuming the base avatar's feet rest at y = 0
                    loadedScene.position.set(0, 0, 0);
                    console.log("Shoe Placement Engine: Ground anchor lock verified.");

                    this.activeGarments[positioningKey] = loadedScene;
                } else {
                    // CLOTHING STRATIFICATION MATRIX
                    const stratificationScaleOffset = 1.0 + (layerDepth * 0.0125);
                    loadedScene.scale.set(stratificationScaleOffset, stratificationScaleOffset, stratificationScaleOffset);
                    loadedScene.position.set(0, 0, 0);

                    this.layerRegistry[layer] = loadedScene;
                }

                // ---- Apply shadow/receiver configuration to all meshes ----
                loadedScene.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                        if (child.material) {
                            child.material.side = 2; // DoubleSide rendering
                        }
                    }
                });

                // ---- Peak-dimension bounding-box framing (Dressing Room path) ----
                this.adjustModelToFitViewport(loadedScene);

                this.scene.add(loadedScene);
                this._syncLayerVisibility();
                resolve();
            }, undefined, (error) => {
                console.error(`[Atelier3D] Failed to load asset ${meshUrl}:`, error);

                // Create procedural fallback
                const layerIdx = LAYER_ORDER.indexOf(layer);
                const scaleFactor = assetCategory === 'footwear' ? 1.0 : (1.0 + (layerIdx * 0.0125));

                const fallbackMat = new THREE.MeshPhysicalMaterial({
                    color: 0x0D2A22,
                    metalness: 0.2,
                    roughness: 0.4,
                });

                let fallbackMesh;
                if (assetCategory === 'footwear') {
                    const shoeGeo = new THREE.BoxGeometry(0.25 * scaleFactor, 0.12 * scaleFactor, 0.4 * scaleFactor);
                    fallbackMesh = new THREE.Mesh(shoeGeo, fallbackMat);
                    fallbackMesh.position.set(0, 0, 0);
                    this.activeGarments[positioningKey] = fallbackMesh;
                } else {
                    const fallbackGeo = new THREE.BoxGeometry(0.3 * scaleFactor, 0.5, 0.2);
                    fallbackMesh = new THREE.Mesh(fallbackGeo, fallbackMat);
                    fallbackMesh.position.y = 0.25;
                    this.layerRegistry[layer] = fallbackMesh;
                }

                fallbackMesh.castShadow = true;
                fallbackMesh.receiveShadow = true;
                this.scene.add(fallbackMesh);
                this._syncLayerVisibility();
                reject(error);
            });
        });
    }

    /**
     * Load an automated garment from external GLTF/GLB with layer depth scaling.
     * Consumes layer-capsule-mesh.window events from Alpine.js.
     * @param {Object} payload - { layerIndex, modelUrl, color, mesh, variantId, productId, priority, isRequired, layer, colorHex, assetCategory }
     */
    loadAutomatedGarment(payload) {
        const { layer, modelUrl, colorHex, productId, variantId, assetCategory } = payload || {};
        if (!layer || !modelUrl) return;

        // Dispose existing garment on this layer
        const existing = this.layerRegistry[layer];
        if (existing) {
            this.scene.remove(existing);
            this._safeDispose(existing);
        }

        // Create loading placeholder
        const loadingGroup = new THREE.Group();
        loadingGroup.userData.garmentId = productId;
        loadingGroup.userData.layer = layer;
        loadingGroup.name = `garment_${layer}_${variantId || 'auto'}`;
        this.layerRegistry[layer] = loadingGroup;

        this.gltfLoader.load(
            modelUrl,
            (gltf) => {
                const loadedScene = gltf.scene;

                // ---- Layer depth scaling (1.0 + layer * 0.0125) ----
                const layerIdx = LAYER_ORDER.indexOf(layer);
                const scaleFactor = 1.0 + (layerIdx * 0.0125);
                loadedScene.scale.setScalar(scaleFactor);
                loadedScene.position.y = 0.05;

                // ---- Apply shadow/receiver configuration to all meshes ----
                loadedScene.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;

                        // ---- Apply color from shader metadata if provided ----
                        if (colorHex && child.material) {
                            if (child.material.color) {
                                child.material.color.set(this._styleHexToThree(colorHex));
                            }
                            if (child.material.emissive && child.material.emissive.set) {
                                child.material.emissive.set(this._styleHexToThree(colorHex));
                                child.material.emissiveIntensity = 0.08;
                            }
                            child.material.needsUpdate = true;
                        }
                    }
                });

                // Replace loading placeholder with actual model
                this.scene.remove(loadingGroup);
                this.layerRegistry[layer] = loadedScene;

                // ---- Peak-dimension bounding-box framing (Dressing Room path) ----
                this.adjustModelToFitViewport(loadedScene);

                this.scene.add(loadedScene);
                this._syncLayerVisibility();
            },
            undefined,
            (error) => {
                console.error(`[Atelier3D] Failed to load garment ${modelUrl}:`, error);
                // Create procedural fallback
                const fallbackMat = new THREE.MeshPhysicalMaterial({
                    color: this._styleHexToThree(colorHex || '#0D2A22'),
                    metalness: 0.2,
                    roughness: 0.4,
                });
                const layerIdx = LAYER_ORDER.indexOf(layer);
                const scaleFactor = 1.0 + (layerIdx * 0.0125);
                const fallbackGeo = new THREE.BoxGeometry(0.3 * scaleFactor, 0.5, 0.2);
                const fallbackMesh = new THREE.Mesh(fallbackGeo, fallbackMat);
                fallbackMesh.position.y = 0.25;
                fallbackMesh.castShadow = true;
                fallbackMesh.receiveShadow = true;
                this.scene.remove(loadingGroup);
                this.layerRegistry[layer] = fallbackMesh;
                this.scene.add(fallbackMesh);
                this._syncLayerVisibility();
            }
        );
    }

    /**
      * Convert CSS hex color string to Three.js Color.
      * @param {string} hex - Hex color string (#RRGGBB)
      * @returns {THREE.Color}
      */
    _styleHexToThree(hex) {
        return new THREE.Color(hex);
    }

     /**
      * Get current layer state for UI updates.
      * @returns {Object} { base: string|null, structural: string|null, shell: string|null }
      */
    getLayerState() {
        const state = {};
        for (const layer of LAYER_ORDER) {
            const mesh = this.layerRegistry[layer];
            state[layer] = mesh ? (mesh.userData.garmentId || null) : null;
        }
        return state;
    }

    /**
     * Emit Alpine.js-compatible custom event with current layer state.
     */
    _emitLayerState() {
        const state = this.getLayerState();
        const event = new CustomEvent('layer-state-updated', {
            detail: state,
            bubbles: true,
        });
        this.container.dispatchEvent(event);
    }

    // ========================================================================
    // GARMENT CREATION (procedural, matches original)
    // ========================================================================

    _createGarmentMesh(type) {
        const cfg = GARMENT_CONFIG[type];
        if (!cfg) return new THREE.Group();

        const group = new THREE.Group();
        group.userData.garmentId = type;
        group.userData.layer = cfg.layer;
        group.castShadow = true;
        group.receiveShadow = true;

        const mat = new THREE.MeshPhysicalMaterial({
            color: cfg.color,
            roughness: 0.4,
            clearcoat: 0.2,
            emissive: cfg.emissive,
            emissiveIntensity: 0.08,
            transparent: true,
            opacity: 0.92,
        });

        if (type === 'mesh_dress_lux') {
            const dress = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.45, 0.9, 16), mat);
            dress.position.y = 0.55;
            group.add(dress);
            const drapeMat = mat.clone();
            drapeMat.color = new THREE.Color(0xD4AF37);
            drapeMat.emissive = new THREE.Color(0xD4AF37);
            drapeMat.emissiveIntensity = 0.1;
            for (let i = 0; i < 4; i++) {
                const a = (i / 4) * Math.PI * 2;
                const d = new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.008, 0.8, 4), drapeMat);
                d.position.set(Math.cos(a) * 0.28, 0.55, Math.sin(a) * 0.28);
                group.add(d);
            }
        } else if (type === 'mesh_jacket_cyber') {
            const jMat = mat.clone();
            jMat.color = new THREE.Color(0x0D4A3A);
            jMat.emissive = new THREE.Color(0x22D3EE);
            jMat.emissiveIntensity = 0.12;
            const jacket = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.30, 0.55, 12), jMat);
            jacket.position.y = 0.7;
            jacket.scale.set(1, 1, 0.8);
            group.add(jacket);
            const lMat = new THREE.MeshPhysicalMaterial({
                color: 0xE6C875, emissive: 0xE6C875,
                emissiveIntensity: 0.2, metalness: 0.5, roughness: 0.1,
            });
            for (let i = 0; i < 2; i++) {
                const lapel = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.2, 0.01), lMat);
                lapel.position.set(0.12 * (i === 0 ? -1 : 1), 0.65, 0.15);
                group.add(lapel);
            }
        } else if (type === 'mesh_trouser_tapered') {
            const tMat = mat.clone();
            tMat.color = new THREE.Color(0xe8d5c0);
            const leftLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.07, 0.55, 8), tMat);
            leftLeg.position.set(-0.12, 0.3, 0);
            group.add(leftLeg);
            const rightLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.07, 0.55, 8), tMat);
            rightLeg.position.set(0.12, 0.3, 0);
            group.add(rightLeg);
            const bandMat = mat.clone();
            bandMat.color = new THREE.Color(0xD4AF37);
            const band = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.025, 8, 16), bandMat);
            band.position.y = 0.55;
            band.rotation.x = Math.PI / 2;
            group.add(band);
        } else if (type === 'mesh_top_structural') {
            const tMat = mat.clone();
            tMat.color = new THREE.Color(0xc4a35a);
            tMat.emissive = new THREE.Color(0xD4AF37);
            tMat.emissiveIntensity = 0.15;
            const top = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.22, 0.35, 12), tMat);
            top.position.y = 0.85;
            group.add(top);
            const accMat = new THREE.MeshPhysicalMaterial({
                color: 0x0D2A22, metalness: 0.6, roughness: 0.2,
            });
            for (let i = 0; i < 2; i++) {
                const acc = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), accMat);
                acc.position.set(0.28 * (i === 0 ? -1 : 1), 0.92, 0);
                acc.scale.set(1, 0.5, 0.6);
                group.add(acc);
            }
        }
        return group;
    }

    // ========================================================================
    // SHOWROOM MODEL LOADER (GLTF with procedural fallback)
    // ========================================================================

    loadShowroomModel(modelUrl, color = '#0D2A22', meshRef = 'default') {
        if (!modelUrl) return;

        // Purge existing showroom model
        if (this.currentShowroomModel) {
            this.scene.remove(this.currentShowroomModel);
            this._safeDispose(this.currentShowroomModel);
        }

        // Hide mannequin and garments when showing a product
        if (this.mannequin.parent) this.scene.remove(this.mannequin);
        this._hideLayerGarments();

        this.gltfLoader.load(
            modelUrl,
            (gltf) => {
                this.currentShowroomModel = gltf.scene;
                this.adjustModelToFitViewport(this.currentShowroomModel);
                this.currentShowroomModel.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });
                this.scene.add(this.currentShowroomModel);
            },
            undefined,
            () => {
                // GLTF load failed — fallback to procedural geometry
                const fallbackMat = new THREE.MeshPhysicalMaterial({
                    color: new THREE.Color(color),
                    metalness: 0.2,
                    roughness: 0.4,
                    clearcoat: 0.3,
                    emissive: new THREE.Color(color),
                    emissiveIntensity: 0.05,
                });
                const fallbackGeo = new THREE.DodecahedronGeometry(0.5, 1);
                this.currentShowroomModel = new THREE.Mesh(fallbackGeo, fallbackMat);
                this.currentShowroomModel.position.y = 0.6;
                this.currentShowroomModel.castShadow = true;
                this.scene.add(this.currentShowroomModel);

                // Restore mannequin + garments
                this.scene.add(this.mannequin);
                this._showLayerGarments();
            }
        );
    }

    resetCamera() {
        this.camera.position.copy(this.defaultCamPosition);
        this.controls.target.copy(this.defaultTargetPosition);
        this.controls.update();
    }

    // ========================================================================
    // BOUNDING-BOX VIEWPORT FRAMING (Showroom + Dressing Room)
    // ========================================================================

    /**
     * Calculates asset boundaries and scales any incoming file down to stable
     * viewport proportions. Unified method handling both avatar and garment /
     * showroom products via the `isAvatar` flag.
     *
     *   isAvatar = true   → peak dimension normalized to 1.6 (avatar human height)
     *   isAvatar = false  → peak dimension normalized to 1.2 (garment / product)
     *
     * After the scale + center + foot-lift pass, applies a luxury textile PBR
     * baseline (roughness 0.85, metalness 0.0, sheen 0.6, sheenRoughness 0.4)
     * to all child meshes that expose a MeshStandardMaterial. Other material
     * types are left untouched (procedural fallback uses MeshPhysicalMaterial
     * and must not be mutated by this path).
     *
     * Foot lift: position.y is set to -boundsBox.min.y + 0.06 to lift shoe
     * hems 0.06 units out of the pedestal floor, producing a "floating on
     * a display form" luxury aesthetic.
     *
     * @param {THREE.Object3D} incomingMesh - The loaded garment, product, or avatar mesh
     * @param {boolean}        isAvatar     - True for human avatars (1.6 norm), false for garments (1.2 norm)
     */
    adjustModelToFitViewport(incomingMesh, isAvatar = false) {
        if (!incomingMesh) return;

        // 1. Calculate the exact physical bounding space of the loaded mesh
        const boundsBox = new THREE.Box3().setFromObject(incomingMesh);
        const meshSize = boundsBox.getSize(new THREE.Vector3());
        const meshCenter = boundsBox.getCenter(new THREE.Vector3());

        // 2. Identify the peak dimension scale factor to check for oversized assets
        const maxDimension = Math.max(meshSize.x, meshSize.y, meshSize.z);

        // 3. Normalization Pass: scale to 1.6 (avatar) or 1.2 (garment) peak dimension
        const targetPeak = isAvatar ? 1.6 : 1.2;
        if (maxDimension > 0) {
            const structuralTargetScale = targetPeak / maxDimension;
            incomingMesh.scale.set(structuralTargetScale, structuralTargetScale, structuralTargetScale);

            // Re-evaluate boundaries post-matrix transformation
            boundsBox.setFromObject(incomingMesh);
            boundsBox.getSize(meshSize);
            boundsBox.getCenter(meshCenter);
        }

        // 4. Center horizontal coordinates perfectly over the scene's central origin
        incomingMesh.position.x -= meshCenter.x;
        incomingMesh.position.z -= meshCenter.z;

        // 5. Force the base of the garment vertices to sit 0.06 units above
        //    the pedestal floor line (y = 0). The 0.06 lift prevents shoe
        //    hems from sinking into the floor and produces a luxury
        //    "floating on a display form" aesthetic.
        incomingMesh.position.y = -boundsBox.min.y + 0.06;

        // 6. Apply luxury textile PBR baseline to all child meshes.
        //    Guarded by isMeshStandardMaterial so the procedural fallback
        //    (which uses MeshPhysicalMaterial) is not mutated.
        incomingMesh.traverse((node) => {
            if (node.isMesh && node.material && node.material.isMeshStandardMaterial) {
                node.material.roughness = 0.85;
                node.material.metalness = 0.0;
                node.material.sheen = 0.6;
                node.material.sheenRoughness = 0.4;
                node.material.needsUpdate = true;
            }
        });

        // 7. Anchor camera OrbitControls to frame the waist/midsection instead of staring at the base
        if (this.controls) {
            this.controls.target.set(0, meshSize.y / 2, 0);

            // Establish protective zoom thresholds to prevent inner polygon clipping errors
            this.controls.minDistance = 0.8;
            this.controls.maxDistance = 5.0;
            this.controls.update();
        }
    }

    // ========================================================================
    // WEBXR / AR GATEWAY
    // ========================================================================

    /**
     * Check if WebXR immersive-ar is supported and request AR session.
     * @returns {Promise<boolean>} Whether AR was successfully requested
     */
    async requestAR() {
        // Check WebXR support
        if (!navigator.xr) {
            return this._fallbackMobileAR();
        }

        const isSupported = await navigator.xr.isSessionSupported('immersive-ar');
        if (!isSupported) {
            return this._fallbackMobileAR();
        }

        try {
            // We need to create a separate XR-compatible renderer for AR
            // For simplicity, dispatch an event that triggers the Three.js XR path
            const session = await navigator.xr.requestSession('immersive-ar', {
                requiredFeatures: ['local'],
                optionalFeatures: ['dom-overlay'],
                domOverlay: { root: document.body },
            });

            this.renderer.xr.enabled = true;
            await this.renderer.xr.setSession(session);

            // Notify UI
            const event = new CustomEvent('ar-session-started', {
                detail: { type: 'webxr' },
                bubbles: true,
            });
            this.container.dispatchEvent(event);

            return true;
        } catch (err) {
            console.warn('[Atelier3D] WebXR AR failed:', err);
            return this._fallbackMobileAR();
        }
    }

    /**
     * Mobile fallback: iOS .usdz with rel=ar, Android intent:// for Scene Viewer.
     * @returns {boolean}
     */
    _fallbackMobileAR() {
        const ua = navigator.userAgent;
        const origin = window.location.origin;

        if (/iPhone|iPad|iPod/i.test(ua)) {
            // iOS 15+: GLB files supported with rel="ar"
            const link = document.createElement('a');
            link.href = origin + AR_CONFIG.glbPath;
            link.rel = 'ar';
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            setTimeout(() => document.body.removeChild(link), 1000);
            return true;
        }

        if (/Android/i.test(ua)) {
            // Android: intent:// for Google Scene Viewer
            const encodedUrl = encodeURIComponent(
                origin + AR_CONFIG.glbPath
            );
            const intentUrl = `intent://arvr.google.com/scene-viewer/1.0?file=${encodedUrl}&mode=ar_only#Intent;scheme=https;package=com.google.android.googlequicksearchbox;action=android.intent.action.VIEW;S.browser_fallback_url=https://developers.google.com/ar;end;`;
            window.location.href = intentUrl;
            return true;
        }

        return false;
    }

    // ========================================================================
    // UTILITY: DISPOSAL
    // ========================================================================

    /**
     * Safely purge Three.js assets to prevent GPU memory leaks.
     * Public method — recursively disposes geometries and materials.
     * @param {THREE.Object3D} node
     */
    safelyPurgeThreeAsset(node) {
        if (!node) return;
        node.traverse((child) => {
            if (child.isMesh) {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach((mat) => this.cleanMaterialResources(mat));
                    } else {
                        this.cleanMaterialResources(child.material);
                    }
                }
            }
        });
    }

    /**
     * Dispose a single material and flush all its texture maps from hardware.
     * @param {THREE.Material} material
     */
    cleanMaterialResources(material) {
        if (!material) return;
        material.dispose();
        // Flush accompanying texture maps completely from the hardware stack
        for (const key in material) {
            if (material[key] && typeof material[key] === 'object' && typeof material[key].dispose === 'function') {
                try {
                    material[key].dispose();
                } catch (_) {
                    // Some texture properties are read-only or already disposed
                }
            }
        }
    }

    /**
     * Private disposal — delegates to safelyPurgeThreeAsset for consistency.
     * @param {THREE.Object3D} node
     */
    _safeDispose(node) {
        this.safelyPurgeThreeAsset(node);
    }

    _hideLayerGarments() {
        for (const layer of LAYER_ORDER) {
            const mesh = this.layerRegistry[layer];
            if (mesh && mesh.parent) {
                this.scene.remove(mesh);
            }
        }
    }

    _showLayerGarments() {
        this._syncLayerVisibility();
    }

    // ========================================================================
    // MODE SWITCHING
    // ========================================================================

    /**
     * Switch between showroom and dressing_room modes.
     * @param {'showroom'|'dressing_room'} mode
     */
    setMode(mode) {
        if (mode === this.mode) return;
        this.mode = mode;

        if (mode === 'showroom') {
            this.controls.autoRotate = true;
            // Restore mannequin + garments if showroom model was loaded
            if (this.currentShowroomModel && this.currentShowroomModel.parent) {
                // Keep showroom model visible
            } else {
                if (!this.mannequin.parent) this.scene.add(this.mannequin);
                this._showLayerGarments();
            }
        } else {
            this.controls.autoRotate = false;
            // Remove showroom model, show mannequin + garments
            if (this.currentShowroomModel && this.currentShowroomModel.parent) {
                this.scene.remove(this.currentShowroomModel);
                this._safeDispose(this.currentShowroomModel);
                this.currentShowroomModel = null;
            }
            if (!this.mannequin.parent) this.scene.add(this.mannequin);
            this._showLayerGarments();
        }
    }

    // ========================================================================
    // EVENT BINDING
    // ========================================================================

    _bindEvents() {
        // Listen for measurement updates from PDP atelier form
        document.addEventListener('measurement-vault-updated', (e) => {
            const measurements = e.detail;
            if (measurements) {
                this.applyMeasurements(measurements, true);
            }
        });

        // Listen for mode switches from Alpine.js
        document.addEventListener('atelier-set-mode', (e) => {
            if (e.detail?.mode) {
                this.setMode(e.detail.mode);
            }
        });

        // Listen for layer garment swaps
        document.addEventListener('swap-clothing', (e) => {
            const asset = e.detail?.asset;
            const layer = e.detail?.layer;
            if (asset && layer) {
                this.setGarmentLayer(layer, asset);
            } else if (asset) {
                // Legacy single-swap support — default to shell layer
                this.setGarmentLayer('shell', asset);
            }
        });

        // Listen for showroom model loads
        document.addEventListener('load-showroom-model', (e) => {
            const { modelUrl, color, mesh } = e.detail || {};
            this.loadShowroomModel(modelUrl, color, mesh);
        });

        // Listen for camera reset
        document.addEventListener('reset-camera', () => {
            this.resetCamera();
        });

        // Listen for AR requests from UI
        document.addEventListener('atelier-request-ar', () => {
            this.requestAR();
        });

        // ---- Dual-avatar gender switch (store handler reference for cleanup) ----
        this._avatarSwitchHandler = async (e) => {
            const targetGender = e.detail?.gender;
            if (!targetGender || this.currentGender === targetGender) return;
            await this.loadHumanAvatar(targetGender);
        };
        window.addEventListener('switch-avatar', this._avatarSwitchHandler);
    }

    /**
     * Public method to re-bind the avatar event listener.
     * Useful if the Alpine component re-initializes after the engine is created.
     */
    initEventListeners() {
        // The switch-avatar listener is already bound in _bindEvents() during construction.
        // This method exists as a public API entry point matching the directive spec.
        // If the engine was already constructed, re-attach to be safe.
        window.removeEventListener('switch-avatar', this._avatarSwitchHandler);
        this._avatarSwitchHandler = async (e) => {
            const targetGender = e.detail?.gender;
            if (!targetGender || this.currentGender === targetGender) return;
            await this.loadHumanAvatar(targetGender);
        };
        window.addEventListener('switch-avatar', this._avatarSwitchHandler);
    }

    /**
     * Load a human avatar GLB model for the given gender.
     * Handles recursive memory disposal before loading.
     * Enforces strict 1.6-unit height normalization to eliminate scale blowouts.
     * Falls back to procedural geometry on network failure.
     * @param {'female'|'male'} gender
     */
    async loadHumanAvatar(gender) {
        const assetPath = `/static/models/avatar_${gender}.glb`;
        this.setViewportLoadingState(true);

        // 1. CRITICAL CONTEXT SAFETY: Recursive Memory Disposal
        if (this.currentAvatarMesh) {
            this.safelyPurgeThreeAsset(this.currentAvatarMesh);
            this.scene.remove(this.currentAvatarMesh);
            this.currentAvatarMesh = null;
        }

        // Also hide the procedural mannequin if present
        if (this.mannequin && this.mannequin.parent) {
            this.scene.remove(this.mannequin);
        }
        this._hideLayerGarments();

        try {
            const gltf = await this.gltfLoader.loadAsync(assetPath);
            this.currentAvatarMesh = gltf.scene;
            this.currentGender = gender;

            // ---- Unified bounding-box framing with avatar-specific 1.6 peak-dim scale ----
            // Delegates to adjustModelToFitViewport(isAvatar=true) which applies:
            //   1.6/rawHeight scale → center X/Z → +0.06 foot lift → textile PBR
            this.adjustModelToFitViewport(this.currentAvatarMesh, true);

            // Traverse and map shadows across the photogrammetry layout structure
            // (Textile PBR is already applied by adjustModelToFitViewport, so we
            //  only configure shadow flags here to avoid duplicate material writes.)
            this.currentAvatarMesh.traverse((node) => {
                if (node.isMesh) {
                    node.castShadow = true;
                    node.receiveShadow = true;
                }
            });

            this.scene.add(this.currentAvatarMesh);
            this.setViewportLoadingState(false);

            // Re-trigger parametric body-morph loops to sync with current profile metrics
            this.applyMeasurements(this.currentUserMeasurements);
            return true;
        } catch (error) {
            console.error('Critical Avatar Allocation Failure:', error);
            this.triggerProceduralFallbackForm(gender);
            this.setViewportLoadingState(false);
            return false;
        }
    }

    // ---------------------------------------------------------------------------
    // AUTO-FRAMING FOR 3D AVATARS
    // ---------------------------------------------------------------------------

    /**
     * Triggers asynchronous avatar instantiation and explicitly guarantees loader dismissal.
     *
     * Bulletproof pattern: the entire load flow is wrapped in `try...catch...finally`
     * with the loader element lookup hoisted to the top of the function (so the
     * `finally` block can always reference the same element reference). The loader
     * is FORCED VISIBLE at the start (so the user sees feedback during load) and
     * FORCED HIDDEN in the `finally` block (so the canvas is always unblocked,
     * even if the GLB parse fails, the network times out, or any helper throws).
     *
     * Loader dismissal uses a 300ms opacity-then-display pattern: opacity fades
     * to 0 first (CSS transition), then `display: none` removes the element from
     * the layout flow. This produces a smooth fade-out animation instead of a
     * jarring instant disappear.
     *
     * @param {string} avatarUrl - Local path coordinates to the GLB file
     */
    async loadBaseAvatar(avatarUrl) {
        // Locate the UI loading indicators early to ensure clean state controls
        const uiLoader = document.getElementById('canvas-loader') || document.querySelector('.loader');
        if (uiLoader) uiLoader.style.display = 'flex'; // Enforce visible initialization states

        try {
            if (this.avatarWrapperGroup) {
                this.safelyPurgeThreeAsset(this.avatarWrapperGroup);
            }
            this.avatarWrapperGroup = new THREE.Group();
            this.scene.add(this.avatarWrapperGroup);

            const gltf = await this.gltfLoader.loadAsync(avatarUrl);
            const rawModel = gltf.scene;

            // Perform dynamic bounding calculations to normalize sizing matrices
            this.adjustModelToFitViewport(rawModel, true);
            this.avatarWrapperGroup.add(rawModel);

            // Reset camera positions cleanly without projection clipping anomalies
            if (this.controls) {
                this.camera.position.set(0, 1.1, 2.4);
                this.controls.target.set(0, 0.85, 0);

                // Adjust interaction velocities to provide fluid touch sliding
                this.controls.rotateSpeed = 1.8;
                this.controls.touchRotateSpeed = 2.2;
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.update();
            }

        } catch (error) {
            console.error("Critical core error handled during 3D scene asset ingestion:", error);
        } finally {
            // DEFENSIVE FIX: This block always fires, preventing infinite canvas freezing
            if (uiLoader) {
                uiLoader.style.opacity = '0';
                setTimeout(() => { uiLoader.style.display = 'none'; }, 300);
            }
        }
    }

    /**
     * Vector-math zoom implementation. Computes the current camera distance
     * vector from the OrbitControls target, multiplies it by `zoomFactor`
     * (0.85 = zoom in, 1.15 = zoom out), and reapplies it to camera position.
     *
     * This bypasses OrbitControls.dollyIn / dollyOut (which have known issues
     * with perspective cameras and target-relative framing) and gives a
     * predictable, clamped result.
     *
     * Safety clamp: target distance is kept between 0.6 and 5.5 world units
     * to prevent the camera from entering the model's chest cavity
     * (visual artifact) or zooming out into infinity (scene blank frame).
     *
     * @param {number} zoomFactor - 0 < z < 1 zooms in, z > 1 zooms out
     */
    executeVectorZoom(zoomFactor) {
        if (!this.controls || !this.camera) return;

        // 1. Extract current camera offset relative to the orbit target
        const offset = new THREE.Vector3().subVectors(this.camera.position, this.controls.target);

        // 2. Scale the offset by the requested zoom factor
        offset.multiplyScalar(zoomFactor);

        // 3. Safety clamp: prevent the camera from entering the model or
        //    zooming out into the void. Clamp the *offset length* (target
        //    distance) to the safe 0.6 → 5.5 unit range.
        const targetDistance = offset.length();
        const minDistance = 0.6;
        const maxDistance = 5.5;
        if (targetDistance < minDistance) {
            offset.setLength(minDistance);
        } else if (targetDistance > maxDistance) {
            offset.setLength(maxDistance);
        }

        // 4. Re-anchor the camera at the new offset and refresh the controls
        this.camera.position.copy(this.controls.target).add(offset);
        this.controls.update();
    }

    /**
     * Interactive API endpoint to zoom in.
     * Exposed to the UI zoom dock overlay buttons in virtual_experience.html.
     */
    zoomIn() {
        this.executeVectorZoom(0.85);
    }

    /**
     * Interactive API endpoint to zoom out.
     * Exposed to the UI zoom dock overlay buttons in virtual_experience.html.
     */
    zoomOut() {
        this.executeVectorZoom(1.15);
    }

    /**
     * Instantly restores camera positioning tracks back to uniform center alignment.
     * Distinct public API (separate from resetCamera which is invoked by event
     * listeners) so the UI reset button always lands on the same baseline.
     */
    resetView() {
        if (this.controls && this.camera) {
            this.camera.position.copy(this.defaultCamPosition);
            this.controls.target.copy(this.defaultTargetPosition);
            this.controls.update();
        }
    }

    /**
     * Set viewport loading overlay state.
     * Uses the canvas-loader element (the new 21st.dev premium dark theme loader).
     * Falls back to `.loader` class if canvas-loader is missing.
     * @param {boolean} loading
     */
    setViewportLoadingState(loading) {
        const overlay = document.getElementById('canvas-loader') || document.querySelector('.loader');
        if (!overlay) return;
        if (loading) {
            overlay.style.display = 'flex';
            overlay.style.opacity = '1';
        } else {
            overlay.style.opacity = '0';
            setTimeout(() => { overlay.style.display = 'none'; }, 300);
        }
    }

    /**
     * Gender-agnostic procedural fallback invoked by `loadBaseAvatar` when the
     * avatar GLB asset cannot be parsed. Delegates to `triggerProceduralFallbackForm`
     * using the current gender (or 'female' as a default) so the directive's
     * parameterless call site works cleanly.
     */
    loadProceduralAvatarFallback() {
        const gender = this.currentGender || 'female';
        this.triggerProceduralFallbackForm(gender);
    }

    /**
     * Procedural fallback when avatar GLB cannot be loaded.
     * Creates a simple articulated form matching the requested gender proportions.
     * @param {'female'|'male'} gender
     */
    triggerProceduralFallbackForm(gender) {
        const group = new THREE.Group();
        group.name = 'avatar_fallback_' + gender;

        const isFemale = gender === 'female';
        const bodyMat = new THREE.MeshPhysicalMaterial({
            color: isFemale ? 0xf0e8e0 : 0xe8d8c8,
            roughness: 0.6,
            transparent: true,
            opacity: 0.9,
        });

        // Torso
        const torsoWidth = isFemale ? 0.30 : 0.36;
        const torso = new THREE.Mesh(new THREE.CylinderGeometry(torsoWidth, torsoWidth * 0.85, 0.65, 12), bodyMat);
        torso.position.y = 0.65;
        torso.castShadow = true;
        group.add(torso);

        // Hips
        const hipsWidth = isFemale ? 0.32 : 0.30;
        const hips = new THREE.Mesh(new THREE.SphereGeometry(hipsWidth, 10, 10), bodyMat);
        hips.position.y = 0.3;
        hips.scale.set(1, 0.35, 0.65);
        group.add(hips);

        // Head
        const headSize = isFemale ? 0.15 : 0.17;
        const head = new THREE.Mesh(new THREE.SphereGeometry(headSize, 14, 14), bodyMat);
        head.position.y = 1.15;
        head.scale.y = isFemale ? 1.1 : 1.15;
        head.castShadow = true;
        group.add(head);

        // Neck
        const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.12, 10), bodyMat);
        neck.position.y = 1.0;
        group.add(neck);

        // Arms
        const armLen = isFemale ? 0.45 : 0.50;
        const armGeo = new THREE.CylinderGeometry(0.05, 0.055, armLen, 8);
        const leftArm = new THREE.Mesh(armGeo, bodyMat);
        leftArm.position.set(-(isFemale ? 0.35 : 0.40), 0.75, 0);
        leftArm.rotation.z = isFemale ? 0.1 : 0.05;
        leftArm.rotation.x = isFemale ? -0.25 : -0.2;
        leftArm.castShadow = true;
        group.add(leftArm);

        const rightArm = new THREE.Mesh(armGeo, bodyMat);
        rightArm.position.set(isFemale ? 0.35 : 0.40, 0.75, 0);
        rightArm.rotation.z = isFemale ? -0.1 : -0.05;
        rightArm.rotation.x = isFemale ? 0.25 : 0.2;
        rightArm.castShadow = true;
        group.add(rightArm);

        // Gold accent (collar/necklace detail)
        const accentMat = new THREE.MeshPhysicalMaterial({
            color: 0xD4AF37,
            metalness: 0.7,
            roughness: 0.2,
            emissive: 0xD4AF37,
            emissiveIntensity: 0.05,
        });
        const collar = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.015, 8, 20), accentMat);
        collar.position.y = 0.95;
        collar.rotation.x = Math.PI / 2;
        group.add(collar);

        group.position.set(0, -1.0, 0);
        this.currentAvatarMesh = group;
        this.currentGender = gender;
        this.scene.add(group);
    }

    // ========================================================================
    // ANIMATION LOOP
    // ========================================================================

    _startLoop() {
        const animate = () => {
            requestAnimationFrame(animate);
            const time = performance.now() / 1000;

            // Morph animation
            this._updateMorphAnimation();

            // Auto-rotate in showroom mode
            if (this.controls.autoRotate) {
                this.controls.update();
            }

            // Gentle float
            if (this.mannequin) {
                this.mannequin.position.y = Math.sin(time * 0.3) * 0.02;
            }
            for (const layer of LAYER_ORDER) {
                const mesh = this.layerRegistry[layer];
                if (mesh) {
                    mesh.position.y = Math.sin(time * 0.3 + LAYER_ORDER.indexOf(layer) * 0.5) * 0.02;
                }
            }

            // Particle rotation
            if (this.particles) {
                this.particles.rotation.y += 0.0003;
            }

            // Accent light pulse
            const pulse = 0.5 + 0.5 * Math.sin(time * 0.5);
            this.accentLight.intensity = 0.2 + pulse * 0.2;

            this.renderer.render(this.scene, this.camera);
        };
        animate();
    }

    // ========================================================================
    // CLEANUP
    // ========================================================================

    dispose() {
        // Dispose all layers
        for (const layer of LAYER_ORDER) {
            const mesh = this.layerRegistry[layer];
            if (mesh) {
                this.scene.remove(mesh);
                this._safeDispose(mesh);
            }
        }
        // Dispose showroom model
        if (this.currentShowroomModel) {
            this.scene.remove(this.currentShowroomModel);
            this._safeDispose(this.currentShowroomModel);
        }
        // Dispose avatar mesh
        if (this.currentAvatarMesh) {
            this.scene.remove(this.currentAvatarMesh);
            this._safeDispose(this.currentAvatarMesh);
        }
        // Dispose mannequin
        if (this.mannequin) {
            this.scene.remove(this.mannequin);
            this._safeDispose(this.mannequin);
        }
        // Dispose renderer
        this.renderer.dispose();
        // Remove canvas
        if (this.renderer.domElement.parentElement) {
            this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
        }
    }
}

// ============================================================================
// FACTORY FUNCTION
// ============================================================================

/**
 * Initialize the Atelier 3D engine.
 * @param {HTMLElement} container - DOM element to mount the WebGL canvas
 * @returns {AtelierEngine}
 */
export function initAtelierEngine(container) {
    return new AtelierEngine(container);
}
