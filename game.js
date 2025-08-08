class Player {
    constructor(game) {
        this.game = game;
        this.size = { width: 3, height: 2 }; // in grid cells

        const initialCol = (this.game.grid.cols - this.size.width) / 2;
        const initialRow = this.game.grid.rows - this.size.height;

        this.pixelPos = this.game.gridToPixel(initialCol, initialRow);
        this.width = this.size.width * this.game.cellSize.width;
        this.turntableRotation = 0;
        this.speed = 500; // pixels per second
        this.velocity = 0;
    }

    draw(ctx) {
        this.width = this.size.width * this.game.cellSize.width;
        const pixelHeight = this.size.height * this.game.cellSize.height;

        // Main body
        ctx.fillStyle = '#333';
        ctx.fillRect(this.pixelPos.x, this.pixelPos.y, this.width, pixelHeight);

        // Turntables
        const turntableRadius = pixelHeight * 0.4;
        const turntableY = this.pixelPos.y + pixelHeight / 2;
        const leftTurntableX = this.pixelPos.x + this.width * 0.25;
        const rightTurntableX = this.pixelPos.x + this.width * 0.75;

        this.drawTurntable(ctx, leftTurntableX, turntableY, turntableRadius, this.turntableRotation);
        this.drawTurntable(ctx, rightTurntableX, turntableY, turntableRadius, -this.turntableRotation);
    }

    drawTurntable(ctx, x, y, radius, rotation) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rotation);

        ctx.fillStyle = '#111';
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = '#555';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, -radius);
        ctx.lineTo(0, radius);
        ctx.stroke();

        ctx.restore();
    }

    update(dt) {
        const prevX = this.pixelPos.x;
        this.pixelPos.x += this.velocity * dt;
        this.pixelPos.x = Math.max(0, Math.min(this.game.canvas.width - this.width, this.pixelPos.x));

        const deltaX = this.pixelPos.x - prevX;
        this.turntableRotation += deltaX * 0.05;
    }

    moveLeft() {
        this.velocity = -this.speed;
    }

    moveRight() {
        this.velocity = this.speed;
    }

    stop() {
        this.velocity = 0;
    }
}

const ENEMY_COLORS = [
    '#ff4136', '#ff851b', '#ffdc00', '#2ecc40', '#0074d9', '#b10dc9',
    '#f012be', '#3d9970', '#01ff70', '#85144b', '#7fdbff', '#39cccc'
];

class Enemy {
    constructor(game, col, row) {
        this.game = game;
        this.gridPos = { col, row };
        this.size = { width: 1, height: 1 }; // in grid cells
        this.color = ENEMY_COLORS[Math.floor(Math.random() * ENEMY_COLORS.length)];
    }

    draw(ctx) {
        const pos = this.game.gridToPixel(this.gridPos.col, this.gridPos.row);
        const size = {
            width: this.size.width * this.game.cellSize.width,
            height: this.size.height * this.game.cellSize.height
        };
        ctx.fillStyle = this.color;
        ctx.fillRect(pos.x + 2, pos.y + 2, size.width - 4, size.height - 4);
    }
}

class Ball {
    constructor(game) {
        this.game = game;
        this.radius = 20; // as per spec
        this.state = 'held';
        this.velocity = { x: 0, y: 0 };
        this.color = '#ffff00'; // Yellow
        this.reset();
    }

    reset() {
        this.state = 'held';
        this.velocity = { x: 0, y: 0 };
        this.color = '#ffff00'; // Reset color to yellow
        this.updateHeldPosition();
    }

    updateHeldPosition() {
        if (this.state === 'held' && this.game.player) {
            this.pos = {
                x: this.game.player.pixelPos.x + this.game.player.width / 2,
                y: this.game.player.pixelPos.y - this.radius
            };
        }
    }

    launch() {
        if (this.state === 'held') {
            this.state = 'moving';
            this.velocity = { x: 100, y: -400 }; // Initial velocity
        }
    }

    update(dt) {
        if (this.state === 'held') {
            this.updateHeldPosition();
        } else if (this.state === 'moving') {
            this.pos.x += this.velocity.x * dt;
            this.pos.y += this.velocity.y * dt;

            this.checkCollisions();
        }
    }

    checkCollisions() {
        // Wall collision
        if (this.pos.x - this.radius < 0 || this.pos.x + this.radius > this.game.canvas.width) {
            this.velocity.x *= -1;
            this.pos.x = Math.max(this.radius, Math.min(this.game.canvas.width - this.radius, this.pos.x));
        }
        if (this.pos.y - this.radius < 0) {
            this.velocity.y *= -1;
            this.pos.y = this.radius;
        }

        // Bottom wall (miss)
        if (this.pos.y + this.radius > this.game.canvas.height) {
            this.reset();
            return; // Exit early since ball is reset
        }

        // Player collision
        const player = this.game.player;
        if (this.pos.y + this.radius > player.pixelPos.y &&
            this.pos.y - this.radius < player.pixelPos.y + (player.size.height * this.game.cellSize.height) &&
            this.pos.x + this.radius > player.pixelPos.x &&
            this.pos.x - this.radius < player.pixelPos.x + player.width) {

            this.velocity.y *= -1;
            this.pos.y = player.pixelPos.y - this.radius; // prevent sticking
            let hitPoint = (this.pos.x - (player.pixelPos.x + player.width / 2)) / (player.width / 2);
            this.velocity.x = hitPoint * 200;
            this.game.playSound(220, 0.1); // Play sound on player hit
        }

        // Enemy collision
        this.game.enemies = this.game.enemies.filter(enemy => {
            const enemyPixelPos = this.game.gridToPixel(enemy.gridPos.col, enemy.gridPos.row);
            const enemyWidth = enemy.size.width * this.game.cellSize.width;
            const enemyHeight = enemy.size.height * this.game.cellSize.height;

            // AABB collision check
            if (this.pos.x + this.radius > enemyPixelPos.x &&
                this.pos.x - this.radius < enemyPixelPos.x + enemyWidth &&
                this.pos.y + this.radius > enemyPixelPos.y &&
                this.pos.y - this.radius < enemyPixelPos.y + enemyHeight) {

                this.velocity.y *= -1; // Simple bounce
                this.game.playSound(440, 0.1);
                this.game.addScore(10);
                this.color = enemy.color;
                return false; // Remove enemy
            }
            return true; // Keep enemy
        });
    }

    draw(ctx) {
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.pos.x, this.pos.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
    }
}

class Trail {
    constructor(pos, radius, color, lifetime) {
        this.pos = { ...pos };
        this.radius = radius;
        this.color = color;
        this.initialLifetime = lifetime;
        this.lifetime = lifetime;
    }

    update(dt) {
        this.lifetime -= dt;
    }

    draw(ctx) {
        const alpha = Math.max(0, this.lifetime / this.initialLifetime);
        ctx.fillStyle = `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${alpha * 0.5})`;
        ctx.beginPath();
        ctx.arc(this.pos.x, this.pos.y, this.radius * (this.lifetime / this.initialLifetime), 0, Math.PI * 2);
        ctx.fill();
    }
}


class Game {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.grid = {
            cols: 24,
            rows: 12
        };
        this.player = null;
        this.ball = null;
        this.enemies = [];
        this.trails = [];
        this.simplex = new SimplexNoise();
        this.lastTime = 0;
        this.audioContext = null;
        this.keys = {};

        this.score = 0;
        this.roundTime = 40;

        // UI elements
        this.scoreEl = document.getElementById('score');
        this.timerEl = document.getElementById('timer');

        this.resize();
        window.addEventListener('resize', () => this.resize());

        this.setupControls();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.cellSize = {
            width: this.canvas.width / this.grid.cols,
            height: this.canvas.height / this.grid.rows
        };
        // No need to call player.updatePixelPos() anymore,
        // as positions are recalculated on the fly or relative to pixels.
    }

    gridToPixel(col, row) {
        return {
            x: col * this.cellSize.width,
            y: row * this.cellSize.height
        };
    }

    pixelToGrid(x, y) {
        return {
            col: Math.floor(x / this.cellSize.width),
            row: Math.floor(y / this.cellSize.height)
        };
    }

    setupControls() {
        window.addEventListener('keydown', e => this.handleKeyDown(e));
        window.addEventListener('keyup', e => this.handleKeyUp(e));

        this.canvas.addEventListener('mousedown', e => {
            if (e.button === 0) { // Left mouse button
                this.launchBall();
            }
        });

        const fireButton = document.getElementById('fire-button');
        fireButton.addEventListener('click', () => this.launchBall());
        fireButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.launchBall();
        });
    }

    handleKeyDown(e) {
        this.keys[e.key] = true;
        if (e.key === 'ArrowLeft') this.player.moveLeft();
        if (e.key === 'ArrowRight') this.player.moveRight();
        if (e.key === ' ') { // Space bar
            this.launchBall();
        }
    }

    handleKeyUp(e) {
        this.keys[e.key] = false;
        if (e.key === 'ArrowLeft' && !this.keys['ArrowRight']) this.player.stop();
        if (e.key === 'ArrowRight' && !this.keys['ArrowLeft']) this.player.stop();
    }

    initAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    playSound(frequency, duration) {
        if (!this.audioContext) return;
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);

        gainNode.gain.setValueAtTime(0.5, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, this.audioContext.currentTime + duration);

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.start();
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    launchBall() {
        this.initAudio(); // Ensure audio is ready on first user interaction
        if (this.ball) {
            this.ball.launch();
        }
    }


    init() {
        this.player = new Player(this);
        this.ball = new Ball(this);
        this.startNewRound();
        console.log("Game initialized");
    }

    startNewRound() {
        this.roundTime = 40;
        this.ball.reset();
        this.generateEnemies();
        this.updateUI();
    }

    addScore(points) {
        this.score += points;
        this.updateUI();
    }

    generateEnemies() {
        this.enemies = [];
        const seed = Date.now();
        const noise = new SimplexNoise(seed);
        const enemyCount = Math.floor(Math.random() * (14 - 4 + 1)) + 4;
        let placedEnemies = 0;

        // Iterate through a central portion of the grid to place enemies
        for (let row = 2; row < 8; row++) {
            for (let col = 2; col < this.grid.cols - 2; col++) {
                if (placedEnemies >= enemyCount) break;
                // Use noise to get a value between -1 and 1
                const noiseVal = noise.noise2D(col * 0.3, row * 0.3);
                if (noiseVal > 0.2) {
                    this.enemies.push(new Enemy(this, col, row));
                    placedEnemies++;
                }
            }
            if (placedEnemies >= enemyCount) break;
        }
    }

    update(dt) {
        if (this.player) {
            this.player.update(dt);
        }
        if (this.ball) {
            this.ball.update(dt);
            if (this.ball.state === 'moving') {
                const trailColor = this.hexToRgb(this.ball.color);
                this.trails.push(new Trail(this.ball.pos, this.ball.radius, trailColor, 1));
            }
        }

        // Update trails
        this.trails.forEach(trail => trail.update(dt));
        this.trails = this.trails.filter(trail => trail.lifetime > 0);

        this.roundTime -= dt;
        if (this.roundTime <= 0) {
            this.startNewRound();
        }

        this.updateUI();
    }

    updateUI() {
        this.scoreEl.textContent = `Score: ${this.score}`;
        this.timerEl.textContent = `Time: ${Math.max(0, Math.ceil(this.roundTime))}`;
    }

    hexToRgb(hex) {
        // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
        const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, (m, r, g, b) => {
            return r + r + g + g + b + b;
        });

        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();

        this.trails.forEach(trail => trail.draw(this.ctx));
        this.enemies.forEach(enemy => enemy.draw(this.ctx));

        if (this.player) {
            this.player.draw(this.ctx);
        }
        if (this.ball) {
            this.ball.draw(this.ctx);
        }
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        this.ctx.lineWidth = 1;
        for (let i = 0; i < this.grid.cols; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(i * this.cellSize.width, 0);
            this.ctx.lineTo(i * this.cellSize.width, this.canvas.height);
            this.ctx.stroke();
        }
        for (let i = 0; i < this.grid.rows; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, i * this.cellSize.height);
            this.ctx.lineTo(this.canvas.width, i * this.cellSize.height);
            this.ctx.stroke();
        }
    }

    gameLoop(timestamp) {
        const dt = (timestamp - this.lastTime) / 1000;
        this.lastTime = timestamp;
        this.update(dt);
        this.render();
        requestAnimationFrame(this.gameLoop.bind(this));
    }

    start() {
        this.init();
        this.gameLoop(0);
    }
}

window.addEventListener('load', () => {
    const canvas = document.getElementById('gameCanvas');
    const game = new Game(canvas);
    game.start();
});
