# ============================================================
#  Простая CNN на PyTorch — распознавание рукописных цифр
#  Датасет: MNIST (60 000 обучающих, 10 000 тестовых изображений)
#  Каждое изображение: 28×28 пикселей, 1 канал (серый), 10 классов (0–9)
# ============================================================

# --- Установка (один раз, в терминале) ---
# pip install torch torchvision


import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader


# ============================================================
# 1. ПОДГОТОВКА ДАННЫХ
# ============================================================

# transforms.Compose — цепочка преобразований, которые применяются к каждому изображению
transform = transforms.Compose([
    transforms.ToTensor(),           # PIL Image (H×W) → тензор (1×H×W), значения 0..1
    transforms.Normalize((0.1307,),  # вычитаем среднее по датасету MNIST
                         (0.3081,))  # делим на стандартное отклонение
    # Нормализация помогает сети учиться быстрее и стабильнее
])

# Скачиваем датасет MNIST (если ещё не скачан — загрузится автоматически)
train_dataset = datasets.MNIST(
    root='./data',    # папка для хранения данных
    train=True,       # обучающая выборка (60 000 изображений)
    download=True,
    transform=transform
)

test_dataset = datasets.MNIST(
    root='./data',
    train=False,      # тестовая выборка (10 000 изображений)
    download=True,
    transform=transform
)

# DataLoader — загружает данные батчами во время обучения
# shuffle=True перемешивает данные в каждой эпохе (важно для обучения)
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
test_loader  = DataLoader(test_dataset,  batch_size=64, shuffle=False)


# ============================================================
# 2. АРХИТЕКТУРА СЕТИ
# ============================================================

class SimpleCNN(nn.Module):
    """
    Архитектура:
      Вход: 1×28×28 (серое изображение MNIST)

      Блок 1: Conv(1→32) → ReLU → MaxPool  → 32×13×13
      Блок 2: Conv(32→64) → ReLU → MaxPool → 64×6×6

      Flatten: 64×6×6 = 2304 числа

      FC1: 2304 → 128 → ReLU → Dropout(0.5)
      FC2: 128 → 10  → (Softmax встроен в loss)

      Выход: вектор из 10 чисел (по числу классов)
    """

    def __init__(self):
        super(SimpleCNN, self).__init__()

        # --- Свёрточная часть ---

        # nn.Conv2d(in_channels, out_channels, kernel_size)
        # in_channels=1  — входное изображение серое (1 канал)
        # out_channels=32 — 32 фильтра, каждый даёт одну feature map
        # kernel_size=3  — фильтр 3×3
        # padding=1      — добавляем нули по краям → размер не уменьшится после свёртки
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3, padding=1)

        # После conv1: 32×28×28
        # После MaxPool(2): 32×14×14

        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        # После conv2: 64×14×14
        # После MaxPool(2): 64×7×7

        # MaxPool2d(2) — берёт максимум из каждого квадрата 2×2, размер делится на 2
        self.pool = nn.MaxPool2d(kernel_size=2)

        # ReLU — функция активации, применяется после каждой свёртки
        self.relu = nn.ReLU()

        # --- Классифицирующая часть ---

        # Dropout — случайно "выключает" нейроны с вероятностью p=0.5
        # Это регуляризация: защита от переобучения
        self.dropout = nn.Dropout(p=0.5)

        # FC1: принимает вектор 64×7×7=3136 чисел, выдаёт 128
        self.fc1 = nn.Linear(in_features=64 * 7 * 7, out_features=128)

        # FC2: принимает 128 чисел, выдаёт 10 (по числу классов 0–9)
        self.fc2 = nn.Linear(in_features=128, out_features=10)

    def forward(self, x):
        """
        Прямой проход — что происходит с данными внутри сети.
        x: тензор формы (batch_size, 1, 28, 28)
        """

        # Блок 1: свёртка → активация → пулинг
        x = self.conv1(x)   # (B, 1, 28, 28) → (B, 32, 28, 28)
        x = self.relu(x)    # отрицательные значения → 0
        x = self.pool(x)    # (B, 32, 28, 28) → (B, 32, 14, 14)

        # Блок 2
        x = self.conv2(x)   # (B, 32, 14, 14) → (B, 64, 14, 14)
        x = self.relu(x)
        x = self.pool(x)    # (B, 64, 14, 14) → (B, 64, 7, 7)

        # Flatten: разворачиваем тензор в вектор
        # -1 означает "автоматически вычислить размер батча"
        x = x.view(-1, 64 * 7 * 7)  # (B, 64, 7, 7) → (B, 3136)

        # Полносвязные слои
        x = self.fc1(x)       # (B, 3136) → (B, 128)
        x = self.relu(x)
        x = self.dropout(x)   # случайно обнуляем 50% нейронов (только при обучении)
        x = self.fc2(x)       # (B, 128) → (B, 10)

        # Возвращаем "сырые" числа (logits), без Softmax
        # CrossEntropyLoss сам применит Softmax внутри — так численно стабильнее
        return x


# ============================================================
# 3. ИНИЦИАЛИЗАЦИЯ
# ============================================================

# Устройство: используем GPU если есть, иначе CPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Используем: {device}")

# Создаём модель и переносим на устройство
model = SimpleCNN().to(device)

# Выводим архитектуру и число параметров
total_params = sum(p.numel() for p in model.parameters())
print(f"Всего параметров: {total_params:,}")
print(model)

# Loss function — функция потерь
# CrossEntropyLoss = Softmax + NLLLoss
# Она сравнивает предсказание сети с правильным ответом
criterion = nn.CrossEntropyLoss()

# Оптимизатор — алгоритм обновления весов
# Adam — один из лучших "по умолчанию": адаптивный learning rate
# lr (learning rate) = шаг обучения, насколько сильно меняем веса за раз
optimizer = optim.Adam(model.parameters(), lr=0.001)


# ============================================================
# 4. ОБУЧЕНИЕ
# ============================================================

def train_epoch(model, loader, criterion, optimizer, device):
    """Один проход по всем обучающим данным (одна эпоха)."""
    model.train()  # включаем режим обучения (Dropout работает)
    total_loss = 0
    correct = 0

    for batch_idx, (images, labels) in enumerate(loader):
        # Переносим данные на устройство (GPU/CPU)
        images, labels = images.to(device), labels.to(device)

        # 1. Обнуляем градиенты с прошлого шага
        optimizer.zero_grad()

        # 2. Прямой проход: получаем предсказания сети
        outputs = model(images)  # форма: (64, 10)

        # 3. Считаем ошибку (loss)
        loss = criterion(outputs, labels)

        # 4. Обратный проход: вычисляем градиенты
        loss.backward()

        # 5. Обновляем веса
        optimizer.step()

        # Статистика
        total_loss += loss.item()
        predicted = outputs.argmax(dim=1)  # берём класс с максимальным значением
        correct += (predicted == labels).sum().item()

        if batch_idx % 200 == 0:
            print(f"  Батч {batch_idx}/{len(loader)}, loss: {loss.item():.4f}")

    accuracy = 100 * correct / len(loader.dataset)
    avg_loss = total_loss / len(loader)
    return avg_loss, accuracy


def evaluate(model, loader, criterion, device):
    """Оцениваем качество на тестовых данных."""
    model.eval()  # выключаем Dropout
    total_loss = 0
    correct = 0

    with torch.no_grad():  # градиенты не нужны при оценке → экономим память
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
            predicted = outputs.argmax(dim=1)
            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / len(loader.dataset)
    avg_loss = total_loss / len(loader)
    return avg_loss, accuracy


# ============================================================
# 5. ЗАПУСК ОБУЧЕНИЯ
# ============================================================

NUM_EPOCHS = 5  # количество проходов по всему датасету

print("\n=== Начинаем обучение ===")
for epoch in range(1, NUM_EPOCHS + 1):
    print(f"\nЭпоха {epoch}/{NUM_EPOCHS}")

    train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
    test_loss, test_acc   = evaluate(model, test_loader, criterion, device)

    print(f"  Train: loss={train_loss:.4f}, accuracy={train_acc:.2f}%")
    print(f"  Test:  loss={test_loss:.4f}, accuracy={test_acc:.2f}%")

print("\n=== Обучение завершено ===")


# ============================================================
# 6. СОХРАНЕНИЕ И ЗАГРУЗКА МОДЕЛИ
# ============================================================

# Сохраняем только веса (рекомендуемый способ)
torch.save(model.state_dict(), 'cnn_mnist.pth')
print("Модель сохранена в cnn_mnist.pth")

# Загрузка:
# model = SimpleCNN()
# model.load_state_dict(torch.load('cnn_mnist.pth'))
# model.eval()


# ============================================================
# 7. ПРЕДСКАЗАНИЕ НА ОДНОМ ИЗОБРАЖЕНИИ
# ============================================================

import random

def predict_single(model, dataset, device):
    """Берём случайное изображение и смотрим что предсказывает сеть."""
    model.eval()
    idx = random.randint(0, len(dataset) - 1)
    image, true_label = dataset[idx]

    # Добавляем batch dimension: (1, 28, 28) → (1, 1, 28, 28)
    image_tensor = image.unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(image_tensor)  # (1, 10)

    # Softmax → вероятности
    probs = torch.softmax(output, dim=1)[0]
    predicted = probs.argmax().item()
    confidence = probs[predicted].item() * 100

    print(f"\nПредсказание: {predicted} (уверенность: {confidence:.1f}%)")
    print(f"Правильный ответ: {true_label}")
    print(f"Правильно: {'Да' if predicted == true_label else 'Нет'}")

predict_single(model, test_dataset, device)


# ============================================================
# ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ
# ============================================================
#
# После 5 эпох:
#   Train accuracy: ~99%
#   Test accuracy:  ~99%
#
# MNIST — простой датасет, наша маленькая CNN справляется отлично.
# Для более сложных задач (CIFAR-10, ImageNet) нужны глубже сети.
#
# ============================================================
