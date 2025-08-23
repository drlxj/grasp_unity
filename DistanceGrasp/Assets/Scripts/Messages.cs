using UnityEngine;

public enum ObjectType
{
    NONE = 0,
    ALARMCLOCK = 1,
    APPLE = 2,
    BANANA = 3,
    BINOCULARS = 4,
    BOWL = 5,
    CAMERA = 6,
    CRACKERBOX = 7,
    CUP = 8,
    DISKLID = 9,
    EYEGLASSES = 10,
    FLASHLIGHT = 11,
    FRYINGPAN = 12,
    GAMEBOARD = 13,
    HAMMER = 14,
    HEADPHONES = 15,
    KNIFE = 16,
    MOUSE = 17,
    MUG = 18,
    PLATE = 19,
    POTTEDMEATCAN = 20,
    SCISSORS = 21,
    SMARTPHONE = 22,
    SPHERELARGE = 23,
    SPHERESMALL = 24,
    STAPLER = 25,
    TEAPOT = 26,
    TOOTHPASTE = 27,
    WATCH = 28,
    WATERINGCAN = 29,
    WINEGLASS = 30,
}

public class ObjectState
{
    public ObjectType objectType;
    // public int objIdx;
    public Quaternion orientation;
//    public Vector3 orientation;
    public Vector3 position;

    public int AddToByteArray(ref byte[] arr, int currentPointer)
    {
        currentPointer = ValueConverter.AddIntToArray(ref arr, currentPointer, (int)objectType);
        // currentPointer = ValueConverter.AddIntToArray(ref arr, currentPointer, objIdx);
        currentPointer = ValueConverter.AddQuaternionToArray(ref arr, currentPointer, orientation);
        // currentPointer = ValueConverter.AddVector3ToArray(ref arr, currentPointer, orientation);
        currentPointer = ValueConverter.AddVector3ToArray(ref arr, currentPointer, position);
        return currentPointer;
    }
}

public class TelemetryMessage
{ 
    public static readonly int JOINT_COUNT = 20;

    public int packetIdx;

    public Quaternion rootRotation = new Quaternion();
    public Vector3 rootPosition = new Vector3();

    public Vector3[] jointPositions = new Vector3[JOINT_COUNT];

    public ObjectState[] objectStates;

    public byte[] ToBytes()
    {
        int newByteCount = 8 + 16 + 12 + JOINT_COUNT * 12 + 4 + (4+4+16+12) * objectStates.Length ;
        byte[] bytes = new byte[newByteCount];

        int currentPointer = 0;
        currentPointer = ValueConverter.AddIntToArray(ref bytes, currentPointer, packetIdx);

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
    public int packetIdx;
    public int objectCount;
    public float[] confidenceScore;
    public int[] objTypesID;
    public Vector3[] objectPositions;

    public CommandMessage(byte[] bytes)
    {
        FromBytes(bytes);
    }



    private void FromBytes(byte[] bytes)
    {
        int currentPointer = 0;
        currentPointer = ValueConverter.ArrayToInt(ref bytes, currentPointer, out packetIdx);
        currentPointer = ValueConverter.ArrayToInt(ref bytes, currentPointer, out objectCount);
        confidenceScore = new float[objectCount];
        objTypesID = new int[objectCount];
        objectPositions = new Vector3[objectCount];

        for (int i = 0; i < objectCount; i++)
        {
            currentPointer = ValueConverter.ArrayToFloat(ref bytes, currentPointer, out confidenceScore[i]);
        }

        for (int i = 0; i < objectCount; i++)
        {
            currentPointer = ValueConverter.ArrayToInt(ref bytes, currentPointer, out objTypesID[i]);
        }

        for (int i = 0; i < objectCount; i++)
        {
            currentPointer = ValueConverter.ArrayToVector3(ref bytes, currentPointer, out objectPositions[i]);
        }
    }
}
