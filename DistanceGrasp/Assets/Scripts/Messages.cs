using UnityEngine;

public enum ObjectType
{
    NONE = 0,
    AIRPLANE = 1,
    CYLINDERSMALL = 2,
    KNIFE = 3,
    STAMP = 4,
    ALARMCLOCK = 5,
    DOORKNOB = 6,
    LIGHTBULB = 7,
    STANFORDBUNNY = 8,
    APPLE = 9,
    DUCK = 10,
    MOUSE = 11,
    STAPLER = 12,
    BANANA = 13,
    ELEPHANT = 14,
    MUG = 15,
    TEAPOT = 16,
    BINOCULARS = 17,
    EYEGLASSES = 18,
    PHONE = 19,
    TOOTHBRUSH = 20,
    BOWL = 21,
    FILENAME = 22,
    PIGGYBANK = 23,
    TOOTHPASTE = 24,
    CAMERA = 25,
    FLASHLIGHT = 26,
    PYRAMIDLARGE = 27,
    TORUSLARGE = 28,
    CUBELARGE = 29,
    FLUTE = 30,
    PYRAMIDMEDIUM = 31,
    TORUSMEDIUM = 32,
    CUBEMEDIUM = 33,
    FRYINGPAN = 34,
    PYRAMIDSMALL = 35,
    TORUSSMALL = 36,
    CUBESMALL = 37,
    GAMECONTROLLER = 38,
    SCISSORS = 39,
    TRAIN = 40,
    CUP = 41,
    HAMMER = 42,
    SPHERELARGE = 43,
    WATCH = 44,
    CYLINDERLARGE = 45,
    HAND = 46,
    SPHEREMEDIUM = 47,
    WATERBOTTLE = 48,
    CYLINDERMEDIUM = 49,
    HEADPHONES = 50,
    SPHERESMALL = 51,
    WINEGLASS = 52
}

public class ObjectState
{
    public ObjectType objectType;
    // public int objIdx;
    public Quaternion orientation;
    public Vector3 position;

    public int AddToByteArray(ref byte[] arr, int currentPointer)
    {
        currentPointer = ValueConverter.AddIntToArray(ref arr, currentPointer, (int)objectType);
        // currentPointer = ValueConverter.AddIntToArray(ref arr, currentPointer, objIdx);
        currentPointer = ValueConverter.AddQuaternionToArray(ref arr, currentPointer, orientation);
        currentPointer = ValueConverter.AddVector3ToArray(ref arr, currentPointer, position);
        return currentPointer;
    }
}

public class TelemetryMessage
{
    public static readonly int JOINT_COUNT = 20;

    public long packetIdx;

    public Quaternion rootRotation = new Quaternion();
    public Vector3 rootPosition = new Vector3();

    public Vector3[] jointPositions = new Vector3[JOINT_COUNT];

    public ObjectState[] objectStates;

    public byte[] ToBytes()
    {
        int newByteCount = 8 + 16 + 12 + JOINT_COUNT * 12 + 4 + (4+4+16+12) * objectStates.Length ;
        byte[] bytes = new byte[newByteCount];

        int currentPointer = 0;
        currentPointer = ValueConverter.AddLongToArray(ref bytes, currentPointer, packetIdx);

        currentPointer = ValueConverter.AddQuaternionToArray(ref bytes, currentPointer, rootRotation);
        currentPointer = ValueConverter.AddVector3ToArray(ref bytes, currentPointer, rootPosition);

        for (int i = 0; i < JOINT_COUNT; i++)
        {
            currentPointer = ValueConverter.AddVector3ToArray(ref bytes, currentPointer, jointPositions[i]);
        }

        currentPointer = ValueConverter.AddIntToArray(ref bytes, currentPointer, objectStates.Length);

        for (int i = 0; i < objectStates.Length; i++)
        {
            currentPointer = objectStates[i].AddToByteArray(ref bytes, currentPointer);
        }

        return bytes;
    }
}

public class CommandMessage
{
    public int objectCount;
    public float[] confidenceScore;
    public Vector3[] objectPositions;

    public CommandMessage(byte[] bytes)
    {
        FromBytes(bytes);
    }

    private void FromBytes(byte[] bytes)
    {
        int currentPointer = 0;
        currentPointer = ValueConverter.ArrayToInt(ref bytes, currentPointer, out objectCount);
        confidenceScore = new float[objectCount];
        objectPositions = new Vector3[objectCount];

        for (int i = 0; i < objectCount; i++)
        {
            currentPointer = ValueConverter.ArrayToFloat(ref bytes, currentPointer, out confidenceScore[i]);
        }

        for (int i = 0; i < objectCount; i++)
        {
            currentPointer = ValueConverter.ArrayToVector3(ref bytes, currentPointer, out objectPositions[i]);
        }
    }
}
