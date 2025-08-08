import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

class Player {
    constructor(game) {
        this.game = game;
        this.size = { width: 3, height: 2 };

        const initialCol = (this.game.grid.cols - this.size.width) / 2;
        const initialRow = 1;

        this.position = this.game.gridToWorld(initialCol, initialRow);

        this.width = this.size.width * this.game.cellSize.width;
        this.height = this.size.height * this.game.cellSize.height;
        this.turntableRotation = 0;
        this.speed = 15;
        this.velocity = 0;

        this.mesh = new THREE.Group();
        const bodyGeom = new THREE.BoxGeometry(this.width, this.height, 1);
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat);
        this.mesh.add(bodyMesh);

        const turntableRadius = this.height * 0.4;
        const turntableGeom = new THREE.CylinderGeometry(turntableRadius, turntableRadius, 0.2, 32);
        const turntableMat = new THREE.MeshStandardMaterial({ color: 0x111111 });

        this.leftTurntable = new THREE.Mesh(turntableGeom, turntableMat);
        this.leftTurntable.position.set(-this.width * 0.25, 0, 0.5);
        this.leftTurntable.rotation.x = Math.PI / 2;
        this.mesh.add(this.leftTurntable);

        this.rightTurntable = new THREE.Mesh(turntableGeom, turntableMat);
        this.rightTurntable.position.set(this.width * 0.25, 0, 0.5);
        this.rightTurntable.rotation.x = Math.PI / 2;
        this.mesh.add(this.rightTurntable);

        this.game.scene.add(this.mesh);
    }

    update(dt) {
        const prevX = this.position.x;
        this.position.x += this.velocity * dt;

        const worldWidth = this.game.grid.cols * this.game.cellSize.width;
        this.position.x = Math.max(-worldWidth/2 + this.width/2, Math.min(worldWidth/2 - this.width/2, this.position.x));

        const deltaX = this.position.x - prevX;
        this.turntableRotation += deltaX * 0.5;

        this.updateMesh();
    }

    updateMesh() {
        this.mesh.position.x = this.position.x;
        this.mesh.position.y = this.position.y;
        this.leftTurntable.rotation.z = this.turntableRotation;
        this.rightTurntable.rotation.z = -this.turntableRotation;
    }

    moveLeft() { this.velocity = -this.speed; }
    moveRight() { this.velocity = this.speed; }
    stop() { this.velocity = 0; }
}

const ENEMY_COLORS = [
    '#ff4136', '#ff851b', '#ffdc00', '#2ecc40', '#0074d9', '#b10dc9',
    '#f012be', '#3d9970', '#01ff70', '#85144b', '#7fdbff', '#39cccc'
];

class Enemy {
    constructor(game, col, row) {
        this.game = game;
        this.gridPos = { col, row };
        this.position = this.game.gridToWorld(col, row);
        this.size = { width: 1, height: 1 };
        this.color = new THREE.Color(ENEMY_COLORS[Math.floor(Math.random() * ENEMY_COLORS.length)]);

        this.mesh = this.game.assets.enemy.clone(true);

        this.mesh.traverse(node => {
            if (node.isMesh) {
                node.material = node.material.clone();
                node.material.color = this.color;
            }
        });

        this.mesh.position.set(this.position.x, this.position.y, 0);
        this.game.scene.add(this.mesh);
    }
}

class Ball {
    constructor(game) {
        this.game = game;
        this.radius = 0.5;
        this.state = 'held';
        this.velocity = new THREE.Vector3(0, 0, 0);
        this.position = new THREE.Vector3(0, 0, 0);
        this.color = new THREE.Color('#ffff00');

        this.mesh = this.game.assets.ball.clone(true);

        const box = new THREE.Box3().setFromObject(this.mesh);
        const size = box.getSize(new THREE.Vector3());
        const scale = (this.radius * 2) / size.y;
        this.mesh.scale.set(scale, scale, scale);

        this.game.scene.add(this.mesh);
        this.reset();
    }

    reset() {
        this.state = 'held';
        this.velocity.set(0, 0, 0);
        this.color.set('#ffff00');
        this.mesh.traverse(node => {
            if(node.isMesh) node.material.color.set(this.color);
        });
        this.updateHeldPosition();
    }

    updateHeldPosition() {
        if (this.state === 'held' && this.game.player) {
            this.position.x = this.game.player.position.x;
            this.position.y = this.game.player.position.y + this.game.player.height / 2 + this.radius;
        }
    }

    launch() {
        if (this.state === 'held') {
            this.state = 'moving';
            this.velocity.set(THREE.MathUtils.randFloat(-2, 2), 15, 0);
        }
    }

    update(dt) {
        if (this.state === 'held') {
            this.updateHeldPosition();
        } else if (this.state === 'moving') {
            this.position.add(this.velocity.clone().multiplyScalar(dt));
            this.checkCollisions();
        }
        this.updateMesh(dt);
    }

    updateMesh(dt) {
        this.mesh.position.copy(this.position);

        const rotationSpeed = 2;
        const axis = new THREE.Vector3(-this.velocity.y, this.velocity.x, 0).normalize();
        const angle = this.velocity.length() * dt / this.radius;

        if (axis.length() > 0.001) {
            const quaternion = new THREE.Quaternion();
            quaternion.setFromAxisAngle(axis, angle);
            this.mesh.quaternion.premultiply(quaternion);
        }
    }

    checkCollisions() {
        const worldWidth = this.game.grid.cols * this.game.cellSize.width;
        const worldHeight = this.game.grid.rows * this.game.cellSize.height;

        if (Math.abs(this.position.x) + this.radius > worldWidth / 2) {
            this.velocity.x *= -1;
            this.position.x = Math.sign(this.position.x) * (worldWidth / 2 - this.radius);
        }
        if (this.position.y + this.radius > worldHeight) {
            this.velocity.y *= -1;
            this.position.y = worldHeight - this.radius;
        }
        if (this.position.y - this.radius < 0) {
            this.reset();
            return;
        }

        const player = this.game.player;
        const ballBox = new THREE.Box3().setFromObject(this.mesh);
        const playerBox = new THREE.Box3().setFromObject(player.mesh);

        if (ballBox.intersectsBox(playerBox)) {
            this.velocity.y *= -1;
            let hitPoint = (this.position.x - player.position.x) / (player.width / 2);
            this.velocity.x = hitPoint * 5;
            this.position.y = player.position.y + player.height / 2 + this.radius;
        }

        this.game.enemies = this.game.enemies.filter(enemy => {
            const enemyBox = new THREE.Box3().setFromObject(enemy.mesh);
            if (ballBox.intersectsBox(enemyBox)) {
                this.velocity.y *= -1;
                this.game.scene.remove(enemy.mesh);
                this.color.set(enemy.color);
                this.mesh.traverse(node => {
                    if(node.isMesh) node.material.color.set(this.color);
                });
                this.game.addScore(10);
                this.game.effects.push(new DeathEffect(this.game, enemy.position, enemy.color));
                return false;
            }
            return true;
        });
    }
}

class DeathEffect {
    constructor(game, position, color) {
        this.game = game;
        this.lifetime = 3;
        this.maxLifetime = 3;

        this.mesh = this.game.assets.enemy.clone(true);
        this.mesh.position.copy(position);

        this.mesh.traverse(node => {
            if (node.isMesh) {
                node.material = node.material.clone();
                node.material.transparent = true;
            }
        });

        this.game.scene.add(this.mesh);
    }

    update(dt) {
        this.lifetime -= dt;
        const progress = this.lifetime / this.maxLifetime;

        const currentScale = 4 * progress;
        this.mesh.scale.set(currentScale, currentScale, currentScale);

        this.mesh.traverse(node => {
            if (node.isMesh) {
                node.material.opacity = progress;
                node.material.color.setHSL((1 - progress) * 2, 1, 0.6);
            }
        });
    }
}

class Game {
    constructor() {
        this.grid = { cols: 24, rows: 12 };
        this.cellSize = { width: 1, height: 1 };
        this.assets = {};
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });

        this.player = null;
        this.ball = null;
        this.enemies = [];
        this.effects = [];
        this.lastTime = 0;
        this.keys = {};
        this.score = 0;
        this.roundTime = 40;
        this.scoreEl = document.getElementById('score');
        this.timerEl = document.getElementById('timer');

        this.init();
    }

    async init() {
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(this.renderer.domElement);
        this.scene.background = new THREE.Color(0x1a023a);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 7.5);
        this.scene.add(directionalLight);

        this.createBoundaries();
        this.camera.position.set(0, this.grid.rows / 2, 22);
        this.camera.lookAt(0, this.grid.rows / 2, 0);

        await this.loadAssets();

        this.player = new Player(this);
        this.ball = new Ball(this);

        this.setupControls();
        this.startNewRound();
        this.gameLoop(0);
    }

    loadAssets() {
        const loader = new GLTFLoader();
        const promises = [];

        promises.push(new Promise(resolve => {
            loader.load('ball.glb',
                (gltf) => resolve(gltf.scene),
                undefined,
                () => {
                    const fallbackGeom = new THREE.SphereGeometry(0.5, 32, 32);
                    const fallbackMat = new THREE.MeshStandardMaterial({ color: 0xffff00 });
                    resolve(new THREE.Mesh(fallbackGeom, fallbackMat));
                }
            );
        }));

        promises.push(new Promise(resolve => {
            loader.load('mainenemy.glb',
                (gltf) => resolve(gltf.scene),
                undefined,
                () => {
                    const fallbackGeom = new THREE.BoxGeometry(this.cellSize.width * 0.9, this.cellSize.height * 0.9, 1);
                    const fallbackMat = new THREE.MeshStandardMaterial({ color: 0xff00ff });
                    resolve(new THREE.Mesh(fallbackGeom, fallbackMat));
                }
            );
        }));

        return Promise.all(promises).then(([ballAsset, enemyAsset]) => {
            this.assets.ball = ballAsset;
            this.assets.enemy = enemyAsset;
        });
    }

    createBoundaries() {
        const worldWidth = this.grid.cols * this.cellSize.width;
        const worldHeight = this.grid.rows * this.cellSize.height;
        const material = new THREE.MeshStandardMaterial({
            color: 0x8888ff, wireframe: true, side: THREE.DoubleSide, transparent: true, opacity: 0.5
        });
        const backWallGeom = new THREE.PlaneGeometry(worldWidth, worldHeight);
        const backWall = new THREE.Mesh(backWallGeom, material);
        backWall.position.set(0, worldHeight / 2, -1);
        this.scene.add(backWall);
        const topWallGeom = new THREE.PlaneGeometry(worldWidth, 1);
        const topWall = new THREE.Mesh(topWallGeom, material);
        topWall.rotation.x = Math.PI / 2;
        topWall.position.set(0, worldHeight, 0);
        this.scene.add(topWall);
    }

    gridToWorld(col, row) {
        const worldWidth = this.grid.cols * this.cellSize.width;
        return new THREE.Vector3(
            (col - this.grid.cols / 2 + 0.5) * this.cellSize.width,
            row * this.cellSize.height + 0.5, 0
        );
    }

    resize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    setupControls() {
        window.addEventListener('resize', () => this.resize());
        window.addEventListener('keydown', e => this.handleKeyDown(e));
        window.addEventListener('keyup', e => this.handleKeyUp(e));
        this.renderer.domElement.addEventListener('mousedown', e => {
            if (e.button === 0) this.launchBall();
        });
        document.getElementById('fire-button').addEventListener('click', () => this.launchBall());
    }

    handleKeyDown(e) {
        this.keys[e.key] = true;
        if (e.key === 'ArrowLeft') this.player.moveLeft();
        if (e.key === 'ArrowRight') this.player.moveRight();
        if (e.key === ' ') this.launchBall();
    }

    handleKeyUp(e) {
        this.keys[e.key] = false;
        if (e.key === 'ArrowLeft' && !this.keys['ArrowRight']) this.player.stop();
        if (e.key === 'ArrowRight' && !this.keys['ArrowLeft']) this.player.stop();
    }

    launchBall() {
        if (this.ball) this.ball.launch();
    }

    startNewRound() {
        this.enemies.forEach(enemy => this.scene.remove(enemy.mesh));
        this.enemies = [];
        this.effects.forEach(effect => this.scene.remove(effect.mesh));
        this.effects = [];
        this.roundTime = 40;
        if(this.ball) this.ball.reset();
        this.generateEnemies();
        this.updateUI();
    }

    generateEnemies() {
        const enemyCount = Math.floor(Math.random() * (14 - 4 + 1)) + 4;
        for (let i = 0; i < enemyCount; i++) {
            const col = Math.floor(Math.random() * (this.grid.cols - 4)) + 2;
            const row = Math.floor(Math.random() * 6) + 5;
            if (!this.enemies.some(e => e.gridPos.col === col && e.gridPos.row === row)) {
                this.enemies.push(new Enemy(this, col, row));
            }
        }
    }

    addScore(points) {
        this.score += points;
    }

    update(dt) {
        if (this.player) this.player.update(dt);
        if (this.ball) this.ball.update(dt);

        this.effects.forEach(effect => effect.update(dt));
        this.effects = this.effects.filter(effect => {
            if (effect.lifetime <= 0) {
                this.scene.remove(effect.mesh);
                return false;
            }
            return true;
        });

        this.roundTime -= dt;
        if (this.roundTime <= 0) this.startNewRound();
        this.updateUI();
    }

    updateUI() {
        this.scoreEl.textContent = `Score: ${this.score}`;
        this.timerEl.textContent = `Time: ${Math.max(0, Math.ceil(this.roundTime))}`;
    }

    render() {
        this.renderer.render(this.scene, this.camera);
    }

    gameLoop(timestamp) {
        const dt = (timestamp - this.lastTime) / 1000 || 0;
        this.lastTime = timestamp;
        this.update(dt);
        this.render();
        requestAnimationFrame(this.gameLoop.bind(this));
    }
}

window.addEventListener('load', () => {
    const game = new Game();
});
