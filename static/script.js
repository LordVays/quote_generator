document.addEventListener('DOMContentLoaded', function() {
    const quoteText = document.getElementById('quoteText');
    const newQuoteBtn = document.getElementById('newQuoteBtn');
    const copyBtn = document.getElementById('copyBtn');
    const tweetBtn = document.getElementById('tweetBtn');
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    const languageSelect = document.getElementById('language');
    
    // Анимация при загрузке новой цитаты
    function animateQuoteChange(newQuote) {
        const quoteBox = document.querySelector('.quote-box');
        quoteBox.classList.remove('fade-in');
        
        setTimeout(() => {
            quoteText.textContent = newQuote;
            quoteBox.classList.add('fade-in');
            
            // Сброс счетчиков лайков
            document.getElementById('likeCount').textContent = '0';
            document.getElementById('dislikeCount').textContent = '0';
        }, 300);
    }
    
    // Получение новой цитаты
    newQuoteBtn.addEventListener('click', async function() {
        try {
            const lang = languageSelect.value;
            const response = await fetch('/new-quote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ language: lang })
            });
            
            const data = await response.json();
            animateQuoteChange(data.quote);
            
            // Показать уведомление
            showNotification(data.message);
        } catch (error) {
            console.error('Error:', error);
            showNotification('Failed to get a new quote. Please try again.');
        }
    });
    
    // Копирование цитаты
    copyBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(quoteText.textContent)
            .then(() => showNotification('Quote copied to clipboard!'))
            .catch(err => console.error('Failed to copy:', err));
    });
    
    // Поделиться в Twitter
    tweetBtn.addEventListener('click', function() {
        const text = encodeURIComponent(quoteText.textContent);
        window.open(`https://twitter.com/intent/tweet?text=${text}`, '_blank');
    });
    
    // Голосование
    likeBtn.addEventListener('click', function() {
        vote('like');
    });
    
    dislikeBtn.addEventListener('click', function() {
        vote('dislike');
    });
    
    async function vote(voteType) {
        try {
            const response = await fetch('/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    quote: quoteText.textContent,
                    vote: voteType
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Обновляем счетчик
                const counter = document.getElementById(`${voteType}Count`);
                counter.textContent = parseInt(counter.textContent) + 1;
                showNotification(data.message);
            } else {
                showNotification(data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('Failed to register vote. Please try again.');
        }
    }
    
    // Изменение языка
    languageSelect.addEventListener('change', function() {
        const lang = this.value;
        window.location.href = `/change-language/${lang}`;
    });
    
    // Всплывающие уведомления
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    // Добавляем стили для уведомлений
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
        }
        
        .notification.show {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
});