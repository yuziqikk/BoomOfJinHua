/**
 * 炸金花游戏前端逻辑
 */

// 游戏状态
let socket = null;
let playerId = null;
let roomId = null;
let gameState = null;
let myCards = [];
let hasLooked = false;
let isMyTurn = false;
let gameHistory = []; // 历史记录

// DOM元素
const screens = {
    lobby: document.getElementById('lobby-screen'),
    waiting: document.getElementById('waiting-screen'),
    game: document.getElementById('game-screen')
};

// ==================== 工具函数 ====================

function showScreen(screenName) {
    Object.values(screens).forEach(s => s.classList.add('hidden'));
    screens[screenName].classList.remove('hidden');
}

function showError(message, elementId = 'lobby-error') {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        setTimeout(() => el.textContent = '', 3000);
    }
    // 同时在控制台输出
    console.error('游戏错误:', message);
    // 如果在游戏界面，显示一个临时提示
    if (screens.game && !screens.game.classList.contains('hidden')) {
        showGameError(message);
    }
}

function showGameError(message) {
    // 创建或获取游戏错误提示元素
    let errorDiv = document.getElementById('game-error-toast');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'game-error-toast';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(231, 76, 60, 0.9);
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            z-index: 2000;
            font-weight: bold;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        `;
        document.body.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 3000);
}

function generatePlayerId() {
    return 'player_' + Math.random().toString(36).substr(2, 9);
}

// ==================== Socket.IO 连接 ====================

function connectSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('已连接到服务器');
    });

    socket.on('connected', (data) => {
        console.log(data.message);
    });

    socket.on('error', (data) => {
        showError(data.message);
    });

    // 房间创建成功
    socket.on('room_created', (data) => {
        playerId = data.player_id;
        roomId = data.room_id;
        roomHostId = data.room.host_id;
        document.getElementById('display-room-id').textContent = roomId;
        updatePlayerList(data.players, data.room.host_id);
        showScreen('waiting');
    });

    // 房间加入成功
    socket.on('room_joined', (data) => {
        playerId = data.player_id;
        roomId = data.room_id;
        roomHostId = data.room.host_id;
        document.getElementById('display-room-id').textContent = roomId;
        updatePlayerList(data.players, data.room.host_id);

        // 如果是重连到进行中的游戏
        if (data.reconnected && data.game_state) {
            gameState = data.game_state;
            const myPlayer = gameState.players.find(p => p.id === playerId);
            if (myPlayer) {
                hasLooked = myPlayer.has_looked;
                myCards = myPlayer.cards || [];
            }
            showScreen('game');
            updateGameUI();
        } else {
            showScreen('waiting');
        }
    });

    // 其他玩家加入
    socket.on('player_joined', (data) => {
        updatePlayerList(data.players, data.host_id);
    });

    // 其他玩家离开
    socket.on('player_left', (data) => {
        if (gameState) {
            // 游戏中有人离开
            updateGameUI();
        } else {
            // 等待中有人离开
            const players = document.querySelectorAll('.player-card');
            players.forEach(p => {
                if (p.dataset.playerId === data.player_id) {
                    p.remove();
                }
            });
        }
    });

    // 游戏开始
    socket.on('game_started', (data) => {
        // 关闭所有弹窗
        closeAllModals();
        document.getElementById('game-over-modal').classList.add('hidden');

        gameState = data.game_state;
        myCards = data.your_cards || [];
        hasLooked = false;
        showScreen('game');
        updateGameUI();
        // 请求历史记录
        socket.emit('get_history', { player_id: playerId });
    });

    // 游戏状态更新
    socket.on('game_update', (data) => {
        gameState = data.game_state;
        updateGameUI();
        // 请求更新历史记录
        socket.emit('get_history', { player_id: playerId });
    });

    // 比牌结果（游戏未结束）
    socket.on('compare_result', (data) => {
        gameState = data.game_state;
        updateGameUI();
        showCompareResult(data.compare_result);
    });

    // 手牌揭示
    socket.on('cards_revealed', (data) => {
        myCards = data.cards;
        hasLooked = true;
        renderMyCards(true);
        updateActionButtons();
    });

    // 游戏结束
    socket.on('game_over', (data) => {
        gameState = data.game_state;
        updateGameUI();
        showGameOver(data.result, data.compare_result);
    });

    // 历史记录更新
    socket.on('history', (data) => {
        gameHistory = data.history;
        renderHistory();
    });
}

// ==================== 大厅功能 ====================

function createRoom() {
    const nickname = document.getElementById('nickname').value.trim();
    if (!nickname) {
        showError('请输入昵称');
        return;
    }

    if (!socket) {
        playerId = generatePlayerId();
        connectSocket();
    }

    socket.emit('create_room', {
        nickname: nickname,
        player_id: playerId
    });
}

function joinRoom() {
    const nickname = document.getElementById('nickname').value.trim();
    const roomIdInput = document.getElementById('room-id').value.trim();

    if (!nickname) {
        showError('请输入昵称');
        return;
    }

    if (!roomIdInput || roomIdInput.length !== 6) {
        showError('请输入6位房间号');
        return;
    }

    if (!socket) {
        playerId = generatePlayerId();
        connectSocket();
    }

    socket.emit('join_room', {
        nickname: nickname,
        room_id: roomIdInput,
        player_id: playerId
    });
}

// ==================== 等待房间功能 ====================

let roomHostId = null; // 房主ID

function updatePlayerList(players, hostId) {
    const container = document.getElementById('player-list');
    container.innerHTML = '';

    // 如果传入了hostId，更新本地记录
    if (hostId) {
        roomHostId = hostId;
    }

    players.forEach(player => {
        const card = document.createElement('div');
        card.className = 'player-card';
        card.dataset.playerId = player.id;

        const isHost = player.id === roomHostId;
        if (isHost) {
            card.classList.add('host');
        }

        let statusText = '等待中';
        if (isHost) {
            statusText = '房主';
        } else if (player.ready) {
            statusText = '已准备';
        }

        card.innerHTML = `
            <div class="name">${player.nickname}</div>
            <div class="status">${statusText}</div>
        `;
        container.appendChild(card);
    });

    // 更新开始按钮状态
    const startBtn = document.getElementById('btn-start');
    if (startBtn) {
        if (playerId === roomHostId) {
            startBtn.textContent = '开始游戏';
            startBtn.disabled = false;
        } else {
            startBtn.textContent = '已准备';
            startBtn.disabled = true;
        }
    }
}

function startGame() {
    socket.emit('start_game', { player_id: playerId });
}

function leaveWaitingRoom() {
    socket.emit('leave_room', { player_id: playerId });
    showScreen('lobby');
    roomId = null;
}

function copyRoomId() {
    navigator.clipboard.writeText(roomId).then(() => {
        alert('房间号已复制: ' + roomId);
    });
}

// ==================== 游戏功能 ====================

function updateGameUI() {
    if (!gameState) return;

    // 更新头部信息
    document.getElementById('game-room-id').textContent = roomId;
    document.getElementById('my-nickname').textContent = gameState.players.find(p => p.id === playerId)?.nickname || '';

    const myPlayer = gameState.players.find(p => p.id === playerId);
    if (myPlayer) {
        document.getElementById('my-points').textContent = myPlayer.points;
        hasLooked = myPlayer.has_looked;
    }

    // 更新积分池
    document.getElementById('pot-value').textContent = gameState.pot;
    document.getElementById('base-bet-value').textContent = gameState.base_bet;

    // 更新其他玩家显示
    renderOtherPlayers();

    // 更新手牌（如果已看牌则显示）
    renderMyCards(hasLooked);

    // 检查是否轮到自己
    isMyTurn = gameState.current_player === playerId && gameState.phase === 'playing';
    updateActionButtons();

    // 显示回合指示
    const turnIndicator = document.getElementById('turn-indicator');
    turnIndicator.classList.remove('hidden', 'my-turn', 'other-turn');

    if (gameState.phase === 'playing') {
        if (isMyTurn) {
            turnIndicator.textContent = '轮到你操作';
            turnIndicator.classList.add('my-turn');
        } else {
            const currentPlayer = gameState.players.find(p => p.id === gameState.current_player);
            turnIndicator.textContent = `${currentPlayer?.nickname || '他人'}回合`;
            turnIndicator.classList.add('other-turn');
        }
    }
}

function renderOtherPlayers() {
    const container = document.getElementById('other-players');
    container.innerHTML = '';

    gameState.players.forEach(player => {
        if (player.id === playerId) return; // 不显示自己

        const card = document.createElement('div');
        card.className = 'other-player-card';

        if (player.id === gameState.current_player) {
            card.classList.add('current');
        }

        if (player.state === 'folded') {
            card.classList.add('folded');
        }

        let statusText = '闷牌';
        let statusClass = 'playing';
        if (player.has_looked) {
            statusText = '看牌';
            statusClass = 'looked';
        }
        if (player.state === 'folded') {
            statusText = '弃牌';
            statusClass = 'folded';
        }

        card.innerHTML = `
            <div class="player-name">${player.nickname}</div>
            <div class="player-points">积分: ${player.points}</div>
            <div class="player-status ${statusClass}">${statusText}</div>
        `;
        card.dataset.playerId = player.id;

        container.appendChild(card);
    });
}

function renderMyCards(showCards) {
    const container = document.getElementById('my-cards');
    container.innerHTML = '';

    for (let i = 0; i < 3; i++) {
        const card = document.createElement('div');
        card.className = 'card';

        if (showCards && myCards[i]) {
            const cardData = myCards[i];
            card.classList.add('front');
            const isRed = cardData.suit === '♥' || cardData.suit === '♦';
            card.classList.add(isRed ? 'red' : 'black');
            card.innerHTML = `
                <div class="suit">${cardData.suit}</div>
                <div class="rank">${cardData.rank}</div>
            `;
        } else {
            card.classList.add('back');
            card.innerHTML = '<div class="suit">?</div>';
        }

        container.appendChild(card);
    }
}

function updateActionButtons() {
    const blindGroup = document.getElementById('blind-bet-group');
    const lookBtn = document.getElementById('btn-look');
    const followBtn = document.getElementById('btn-follow');
    const foldBtn = document.getElementById('btn-fold');
    const compareBtn = document.getElementById('btn-compare');

    const myPlayer = gameState?.players.find(p => p.id === playerId);
    const isFolded = myPlayer?.state === 'folded';
    const currentBaseBet = gameState?.base_bet || 0;

    // 禁用所有按钮如果不是自己的回合或已弃牌（看牌按钮除外）
    const disabled = !isMyTurn || isFolded;

    // 闷牌按钮组 (未看牌时显示)
    blindGroup.classList.toggle('hidden', hasLooked);
    blindGroup.querySelectorAll('button').forEach(btn => {
        const amount = parseInt(btn.dataset.amount);
        // 闷4（最大值）始终可用，其他金额不能低于底注
        const isMaxBet = amount === 4;
        const belowBaseBet = currentBaseBet > 0 && amount < currentBaseBet;
        // 闷4永远不因为底注而禁用，只因为不是自己回合而禁用
        const shouldDisable = disabled || (!isMaxBet && belowBaseBet);
        btn.disabled = shouldDisable;

        // 添加视觉提示
        if (!isMaxBet && belowBaseBet) {
            btn.classList.add('disabled-bet');
            btn.title = `不能低于底注(${currentBaseBet})`;
        } else {
            btn.classList.remove('disabled-bet');
            btn.title = isMaxBet ? '最大闷牌金额，始终可用' : '';
        }
    });

    // 看牌按钮 (未看牌时显示，随时可点击)
    lookBtn.classList.toggle('hidden', hasLooked);
    lookBtn.disabled = isFolded; // 只有弃牌时才禁用

    // 跟牌按钮 (已看牌时显示)
    followBtn.classList.toggle('hidden', !hasLooked);
    followBtn.disabled = disabled;

    // 如果已看牌但底注为0，显示下注选项
    if (hasLooked && currentBaseBet === 0) {
        followBtn.textContent = '下注';
        followBtn.onclick = () => showBetOptions();
    } else if (currentBaseBet > 0) {
        followBtn.textContent = `跟牌(${currentBaseBet * 2})`;
        followBtn.onclick = () => handleAction('follow');
    } else {
        followBtn.textContent = '跟牌';
    }

    // 弃牌按钮
    foldBtn.disabled = disabled;

    // 开牌按钮
    compareBtn.classList.remove('hidden');
    compareBtn.disabled = disabled;
}

function showBetOptions() {
    // 显示下注选项弹窗（已看牌但底注为0时）
    let modal = document.getElementById('bet-options-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'bet-options-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="modal-content">
            <h3>选择下注金额</h3>
            <div class="bet-options">
                <button class="btn btn-action" onclick="doBet(1)">下注 1</button>
                <button class="btn btn-action" onclick="doBet(2)">下注 2</button>
                <button class="btn btn-action" onclick="doBet(4)">下注 4</button>
            </div>
            <button class="btn btn-secondary" onclick="closeBetOptions()" style="margin-top: 15px;">取消</button>
        </div>
    `;
    modal.classList.remove('hidden');
}

function doBet(amount) {
    closeBetOptions();
    socket.emit('follow', {
        player_id: playerId,
        amount: amount
    });
}

function closeBetOptions() {
    const modal = document.getElementById('bet-options-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function handleAction(action, data = {}) {
    // 看牌操作随时可以执行
    if (action === 'look') {
        socket.emit('look_cards', { player_id: playerId });
        return;
    }

    // 其他操作需要轮到自己
    if (!isMyTurn) return;

    switch (action) {
        case 'blind':
            socket.emit('blind_bet', {
                player_id: playerId,
                amount: data.amount
            });
            break;

        case 'look':
            socket.emit('look_cards', { player_id: playerId });
            break;

        case 'follow':
            socket.emit('follow', { player_id: playerId });
            break;

        case 'fold':
            socket.emit('fold', { player_id: playerId });
            break;

        case 'compare':
            showCompareModal();
            break;
    }
}

function showCompareModal() {
    const modal = document.getElementById('compare-modal');
    const targetsContainer = document.getElementById('compare-targets');
    targetsContainer.innerHTML = '';

    // 获取可比较的玩家
    gameState.players.forEach(player => {
        if (player.id === playerId) return;
        if (player.state === 'folded') return;

        const btn = document.createElement('button');
        btn.className = 'compare-target-btn';
        btn.textContent = player.nickname;
        btn.onclick = () => {
            socket.emit('compare', {
                player_id: playerId,
                target_id: player.id
            });
            modal.classList.add('hidden');
        };
        targetsContainer.appendChild(btn);
    });

    if (targetsContainer.children.length === 0) {
        showError('没有可比牌的玩家');
        return;
    }

    modal.classList.remove('hidden');
}

function hideCompareModal() {
    document.getElementById('compare-modal').classList.add('hidden');
}

function showCompareResult(compareResult) {
    // 先关闭其他弹窗
    closeAllModals();

    // 显示比牌结果弹窗（游戏未结束）
    let modal = document.getElementById('compare-result-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'compare-result-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    // 如果只剩两人开牌，显示双方牌面
    if (compareResult.both_looked) {
        showCardRevealAnimationNonGameOver(compareResult);
        return;
    }

    // 检查自己是否是输家（游戏未结束，只是输了这轮比牌）
    if (compareResult.loser === playerId) {
        showLoserCardsNonGameOver(compareResult);
        return;
    }

    // 普通显示
    modal.innerHTML = `
        <div class="modal-content">
            <h3>比牌结果</h3>
            <div class="compare-winner">
                <div>赢家: <strong>${compareResult.winner_nickname}</strong></div>
                <div style="color: #888; margin-top: 10px;">${compareResult.loser_nickname} 弃牌</div>
            </div>
            <button class="btn btn-primary" onclick="closeCompareResultModal()">确定</button>
        </div>
    `;
    modal.classList.remove('hidden');
}

function closeCompareResultModal() {
    const modal = document.getElementById('compare-result-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function showGameOver(result, compareResult) {
    // 先关闭所有可能存在的弹窗
    closeAllModals();

    const modal = document.getElementById('game-over-modal');
    const winnerInfo = document.getElementById('winner-info');
    const finalPot = document.getElementById('final-pot');

    // 如果只剩两人开牌，显示双方牌面（无论输赢）
    if (compareResult && compareResult.both_looked) {
        showCardRevealAnimation(compareResult, result);
        return;
    }

    // 检查自己是否是输家，显示自己的牌
    if (compareResult && compareResult.loser === playerId) {
        showLoserCards(compareResult, result);
        return;
    }

    winnerInfo.innerHTML = `
        <div>赢家: <strong>${result.winner_nickname}</strong></div>
    `;
    finalPot.innerHTML = `获得积分: <strong>${result.pot}</strong>`;

    modal.classList.remove('hidden');
}

function closeAllModals() {
    // 关闭所有弹窗
    const modals = ['compare-result-modal', 'card-reveal-modal', 'loser-cards-modal', 'compare-modal'];
    modals.forEach(id => {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('hidden');
        }
    });
}

function showLoserCards(compareResult, result) {
    // 创建输家看牌弹窗
    let modal = document.getElementById('loser-cards-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'loser-cards-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    const loserCards = compareResult.loser_cards || [];
    const loserHandType = compareResult.loser_hand_type || '';

    modal.innerHTML = `
        <div class="modal-content card-reveal-content">
            <h3>开牌结果</h3>
            <div class="loser-info">
                <div class="loser-message">你输了！</div>
                <div class="your-cards-label">你的底牌</div>
                <div class="reveal-cards" id="loser-reveal-cards"></div>
                <div class="hand-type">${loserHandType}</div>
            </div>
            <div class="winner-info-small">
                赢家: <strong>${result.winner_nickname}</strong>
            </div>
            <div class="pot-info-small">获得积分: ${result.pot}</div>
            <button class="btn btn-primary" onclick="closeLoserCardsAndShowGameOver('${result.winner_nickname}', ${result.pot})">确定</button>
        </div>
    `;

    modal.classList.remove('hidden');

    // 显示输家的牌
    const cardsContainer = document.getElementById('loser-reveal-cards');
    loserCards.forEach((cardData, index) => {
        setTimeout(() => {
            cardsContainer.appendChild(createRevealCard(cardData));
        }, index * 500);
    });
}

function closeLoserCardsAndShowGameOver(winnerName, pot) {
    // 先关闭所有弹窗
    closeAllModals();

    const gameOverModal = document.getElementById('game-over-modal');
    document.getElementById('winner-info').innerHTML = `
        <div>赢家: <strong>${winnerName}</strong></div>
    `;
    document.getElementById('final-pot').innerHTML = `获得积分: <strong>${pot}</strong>`;
    gameOverModal.classList.remove('hidden');
}

function showCardRevealAnimation(compareResult, result) {
    // 创建揭示牌面弹窗
    let modal = document.getElementById('card-reveal-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'card-reveal-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="modal-content card-reveal-content">
            <h3>开牌比牌</h3>
            <div class="reveal-players">
                <div class="reveal-player">
                    <div class="player-name">${compareResult.player_nickname}</div>
                    <div class="reveal-cards" id="player-reveal-cards"></div>
                    <div class="hand-type" id="player-hand-type"></div>
                </div>
                <div class="vs-divider">VS</div>
                <div class="reveal-player">
                    <div class="player-name">${compareResult.target_nickname}</div>
                    <div class="reveal-cards" id="target-reveal-cards"></div>
                    <div class="hand-type" id="target-hand-type"></div>
                </div>
            </div>
            <div class="reveal-result hidden" id="reveal-result"></div>
        </div>
    `;

    modal.classList.remove('hidden');

    // 一张一张揭示牌面
    const playerCards = compareResult.player_cards;
    const targetCards = compareResult.target_cards;
    let cardIndex = 0;

    function revealNextCard() {
        if (cardIndex >= 3) {
            // 所有牌揭示完毕，显示牌型和结果
            setTimeout(() => {
                document.getElementById('player-hand-type').textContent = compareResult.player_hand_type;
                document.getElementById('target-hand-type').textContent = compareResult.target_hand_type;

                const resultDiv = document.getElementById('reveal-result');
                resultDiv.innerHTML = `
                    <div class="winner-announce">赢家: <strong>${result.winner_nickname}</strong></div>
                    <div class="pot-won">获得积分: ${result.pot}</div>
                    <button class="btn btn-primary" onclick="closeCardRevealAndShowGameOver('${result.winner_nickname}', ${result.pot})">确定</button>
                `;
                resultDiv.classList.remove('hidden');
            }, 500);
            return;
        }

        // 揭示第cardIndex张牌
        setTimeout(() => {
            const playerContainer = document.getElementById('player-reveal-cards');
            const targetContainer = document.getElementById('target-reveal-cards');

            if (playerCards[cardIndex]) {
                playerContainer.appendChild(createRevealCard(playerCards[cardIndex]));
            }
            if (targetCards[cardIndex]) {
                targetContainer.appendChild(createRevealCard(targetCards[cardIndex]));
            }

            cardIndex++;
            revealNextCard();
        }, 800);
    }

    // 开始揭示
    setTimeout(revealNextCard, 500);
}

function createRevealCard(cardData) {
    const card = document.createElement('div');
    card.className = 'reveal-card';
    const isRed = cardData.suit === '♥' || cardData.suit === '♦';
    card.classList.add(isRed ? 'red' : 'black');
    card.innerHTML = `
        <div class="card-suit">${cardData.suit}</div>
        <div class="card-rank">${cardData.rank}</div>
    `;
    return card;
}

function closeCardRevealAndShowGameOver(winnerName, pot) {
    // 先关闭所有弹窗
    closeAllModals();

    const gameOverModal = document.getElementById('game-over-modal');
    document.getElementById('winner-info').innerHTML = `
        <div>赢家: <strong>${winnerName}</strong></div>
    `;
    document.getElementById('final-pot').innerHTML = `获得积分: <strong>${pot}</strong>`;
    gameOverModal.classList.remove('hidden');
}

// 游戏未结束时的输家显示（只是输了这轮比牌，游戏继续）
function showLoserCardsNonGameOver(compareResult) {
    let modal = document.getElementById('loser-cards-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'loser-cards-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    const loserCards = compareResult.loser_cards || [];
    const loserHandType = compareResult.loser_hand_type || '';

    modal.innerHTML = `
        <div class="modal-content card-reveal-content">
            <h3>比牌结果</h3>
            <div class="loser-info">
                <div class="loser-message">你输了！</div>
                <div class="your-cards-label">你的底牌</div>
                <div class="reveal-cards" id="loser-reveal-cards"></div>
                <div class="hand-type">${loserHandType}</div>
            </div>
            <div class="winner-info-small">
                赢家: <strong>${compareResult.winner_nickname}</strong>
            </div>
            <button class="btn btn-primary" onclick="closeLoserCardsModal()">确定</button>
        </div>
    `;

    modal.classList.remove('hidden');

    // 显示输家的牌
    const cardsContainer = document.getElementById('loser-reveal-cards');
    loserCards.forEach((cardData, index) => {
        setTimeout(() => {
            cardsContainer.appendChild(createRevealCard(cardData));
        }, index * 500);
    });
}

function closeLoserCardsModal() {
    const modal = document.getElementById('loser-cards-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// 游戏未结束时的双方看牌揭示动画
function showCardRevealAnimationNonGameOver(compareResult) {
    let modal = document.getElementById('card-reveal-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'card-reveal-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="modal-content card-reveal-content">
            <h3>开牌比牌</h3>
            <div class="reveal-players">
                <div class="reveal-player">
                    <div class="player-name">${compareResult.player_nickname}</div>
                    <div class="reveal-cards" id="player-reveal-cards"></div>
                    <div class="hand-type" id="player-hand-type"></div>
                </div>
                <div class="vs-divider">VS</div>
                <div class="reveal-player">
                    <div class="player-name">${compareResult.target_nickname}</div>
                    <div class="reveal-cards" id="target-reveal-cards"></div>
                    <div class="hand-type" id="target-hand-type"></div>
                </div>
            </div>
            <div class="reveal-result hidden" id="reveal-result"></div>
        </div>
    `;

    modal.classList.remove('hidden');

    // 一张一张揭示牌面
    const playerCards = compareResult.player_cards;
    const targetCards = compareResult.target_cards;
    let cardIndex = 0;

    function revealNextCard() {
        if (cardIndex >= 3) {
            // 所有牌揭示完毕，显示牌型和结果
            setTimeout(() => {
                document.getElementById('player-hand-type').textContent = compareResult.player_hand_type;
                document.getElementById('target-hand-type').textContent = compareResult.target_hand_type;

                const resultDiv = document.getElementById('reveal-result');
                resultDiv.innerHTML = `
                    <div class="winner-announce">赢家: <strong>${compareResult.winner_nickname}</strong></div>
                    <button class="btn btn-primary" onclick="closeCardRevealModal()">确定</button>
                `;
                resultDiv.classList.remove('hidden');
            }, 500);
            return;
        }

        // 揭示第cardIndex张牌
        setTimeout(() => {
            const playerContainer = document.getElementById('player-reveal-cards');
            const targetContainer = document.getElementById('target-reveal-cards');

            if (playerCards[cardIndex]) {
                playerContainer.appendChild(createRevealCard(playerCards[cardIndex]));
            }
            if (targetCards[cardIndex]) {
                targetContainer.appendChild(createRevealCard(targetCards[cardIndex]));
            }

            cardIndex++;
            revealNextCard();
        }, 800);
    }

    // 开始揭示
    setTimeout(revealNextCard, 500);
}

function closeCardRevealModal() {
    const modal = document.getElementById('card-reveal-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function startNewGame() {
    // 关闭所有弹窗
    closeAllModals();
    document.getElementById('game-over-modal').classList.add('hidden');
    socket.emit('new_game', { player_id: playerId });
}

// ==================== 历史记录功能 ====================

function renderHistory() {
    const container = document.getElementById('history-list');
    if (!container) return;

    container.innerHTML = '';

    if (!gameHistory || gameHistory.length === 0) {
        container.innerHTML = '<div class="history-item" style="color: #888;">暂无记录</div>';
        return;
    }

    gameHistory.forEach((record, index) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        // 根据动作类型添加特殊样式
        if (record.action === 'game_start') {
            item.classList.add('game-start');
        } else if (record.action === 'game_over') {
            item.classList.add('game-over');
        } else if (record.action === 'new_game') {
            item.classList.add('new-game');
        }

        const roundText = `第${record.round}回合`;
        let actionText = '';

        switch (record.action) {
            case 'game_start':
                actionText = `游戏开始 - ${record.data.players?.join(', ') || ''}`;
                break;
            case 'look':
                actionText = `<span class="nickname">${record.player_nickname}</span> 看牌`;
                break;
            case 'blind_bet':
                actionText = `<span class="nickname">${record.player_nickname}</span> 闷牌 <span class="amount">${record.data.amount}</span>`;
                break;
            case 'follow':
                actionText = `<span class="nickname">${record.player_nickname}</span> 跟牌 <span class="amount">${record.data.amount}</span>`;
                break;
            case 'fold':
                actionText = `<span class="nickname">${record.player_nickname}</span> 弃牌`;
                break;
            case 'compare':
                actionText = `<span class="nickname">${record.player_nickname}</span> 开牌比 <span class="nickname">${record.data.target_nickname}</span>，<span class="nickname">${record.data.winner_nickname}</span> 获胜`;
                break;
            case 'game_over':
                actionText = `游戏结束 - <span class="nickname">${record.data.winner}</span> 获胜，赢得 <span class="amount">${record.data.pot}</span> 积分`;
                break;
            default:
                actionText = `${record.player_nickname} ${record.action}`;
        }

        item.innerHTML = `
            <div class="round">${roundText}</div>
            <div class="action">${actionText}</div>
        `;

        container.appendChild(item);
    });

    // 滚动到底部
    container.scrollTop = container.scrollHeight;
}

function toggleHistoryPanel() {
    const panel = document.querySelector('.history-panel');
    const btn = document.getElementById('btn-toggle-history');
    if (panel.classList.contains('collapsed')) {
        panel.classList.remove('collapsed');
        btn.textContent = '收起';
    } else {
        panel.classList.add('collapsed');
        btn.textContent = '展开';
    }
}

// ==================== 事件绑定 ====================

document.addEventListener('DOMContentLoaded', () => {
    // 大厅按钮
    document.getElementById('btn-create').addEventListener('click', createRoom);
    document.getElementById('btn-join').addEventListener('click', joinRoom);

    // 等待房间按钮
    document.getElementById('btn-start').addEventListener('click', startGame);
    document.getElementById('btn-leave-waiting').addEventListener('click', leaveWaitingRoom);
    document.getElementById('btn-copy-room').addEventListener('click', copyRoomId);

    // 游戏操作按钮
    document.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            const amount = parseInt(btn.dataset.amount) || null;
            handleAction(action, { amount });
        });
    });

    // 比牌弹窗
    document.getElementById('btn-cancel-compare').addEventListener('click', hideCompareModal);

    // 新游戏
    document.getElementById('btn-new-game').addEventListener('click', startNewGame);

    // 历史记录面板
    document.getElementById('btn-toggle-history').addEventListener('click', toggleHistoryPanel);

    // Enter键快捷操作
    document.getElementById('nickname').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createRoom();
    });

    document.getElementById('room-id').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') joinRoom();
    });
});
