# Use official Gradle image with Java 17 which includes all necessary tools
FROM gradle:8.11.1-jdk17-jammy

# Install Python and Android SDK dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set up Android SDK
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools

# Create Android SDK directory
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools

# Download and install Android command line tools
RUN wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmdline-tools.zip && \
    unzip -q /tmp/cmdline-tools.zip -d ${ANDROID_HOME}/cmdline-tools && \
    mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest && \
    rm /tmp/cmdline-tools.zip

# Accept licenses
RUN yes | sdkmanager --licenses || true

# Pre-install common SDK components to speed up builds
RUN sdkmanager "platform-tools" "platforms;android-35" "build-tools;34.0.0" || true

# Install Python dependencies from pyproject.toml
# A stub module is created so pip can resolve the package; the real source is volume-mounted.
COPY pyproject.toml /tmp/build/pyproject.toml
RUN pip3 install --no-cache-dir 'setuptools>=68' && \
    touch /tmp/build/generate_app.py && \
    pip3 install --no-cache-dir --no-build-isolation /tmp/build && \
    rm -rf /tmp/build

WORKDIR /workspace

CMD ["python3", "src/generate_app.py", "--help"]
