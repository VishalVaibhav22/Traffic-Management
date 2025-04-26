# Required Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns

# Step 1: Create a better dataset (more realistic)
np.random.seed(42)  # For reproducibility

# Generate 1000 samples
data_size = 1000

# Simulate time of day (0-23)
time_of_day = np.random.randint(0, 24, size=data_size)

# Simulate weather (0: Clear, 1: Rainy, 2: Foggy)
weather = np.random.choice([0,1,2], size=data_size, p=[0.7, 0.2, 0.1])

# Simulate day of week (0: Monday, 6: Sunday)
day_of_week = np.random.randint(0, 7, size=data_size)

# Traffic Density (0: Low, 1: High)
# Rough rules:
# - Morning (7-10 AM) and Evening (5-8 PM) usually High density
# - Rainy weather increases density
# - Weekends (Saturday/Sunday) lower density
traffic_density = []
for t, w, d in zip(time_of_day, weather, day_of_week):
    prob = 0.2
    if (7 <= t <= 10) or (17 <= t <= 20):
        prob += 0.5
    if w == 1:  # Rainy
        prob += 0.2
    if d >=5:  # Weekend
        prob -= 0.2
    prob = min(max(prob, 0), 1)
    traffic_density.append(np.random.choice([1, 0], p=[prob, 1-prob]))

# Create DataFrame
df = pd.DataFrame({
    'TimeOfDay': time_of_day,
    'Weather': weather,
    'DayOfWeek': day_of_week,
    'TrafficDensity': traffic_density
})

# Save dataset
df.to_csv('traffic_dataset.csv', index=False)

# Step 2: Visualizations
plt.figure(figsize=(10,6))
sns.countplot(data=df, x='TimeOfDay', hue='TrafficDensity', palette='coolwarm')
plt.title('Traffic Density vs Time of Day')
plt.xlabel('Hour of the Day')
plt.ylabel('Count')
plt.legend(labels=['Low','High'])
plt.show()

plt.figure(figsize=(8,5))
sns.countplot(data=df, x='Weather', hue='TrafficDensity', palette='Set2')
plt.title('Traffic Density by Weather')
plt.xticks(ticks=[0,1,2], labels=['Clear','Rainy','Foggy'])
plt.show()

# Step 3: Model Training
X = df[['TimeOfDay', 'Weather', 'DayOfWeek']]
y = df['TrafficDensity']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

model = LogisticRegression()
model.fit(X_train, y_train)

# Step 4: Model Evaluation
y_pred = model.predict(X_test)

acc = accuracy_score(y_test, y_pred)
print(f"\nModel Accuracy: {acc*100:.2f}%\n")

print("Classification Report:")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.show()

# Step 5: Make Predictions
new_data = pd.DataFrame({
    'TimeOfDay': [12],
    'Weather': [0],
    'DayOfWeek': [3]
})

prediction = model.predict(new_data)
print(f"Predicted Traffic Density: {'High' if prediction[0] else 'Low'}")